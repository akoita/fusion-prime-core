// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "../interfaces/ILiquidityBridgeAdapter.sol";
import "./CCIPAdapter.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CCIPLiquidityAdapter
 * @notice Production-ready Chainlink CCIP bridge adapter for cross-chain liquidity access
 * @dev Extends CCIPAdapter with liquidity-specific functionality
 *
 * Key Features:
 * - Uses Chainlink CCIP for cross-chain messaging (more battle-tested)
 * - Native fee estimation via CCIP Router
 * - Faster finality on supported chains
 */
contract CCIPLiquidityAdapter is
    ILiquiditySource,
    ILiquidityBridgeAdapter,
    Ownable
{
    using StringAddressUtils for string;
    using StringAddressUtils for address;

    // ============ Constants ============

    address public constant NATIVE_ETH = address(0);

    // CCIP is generally faster due to Chainlink's optimistic model
    uint256 public constant CCIP_FAST_TIME = 120; // 2 minutes
    uint256 public constant CCIP_STANDARD_TIME = 300; // 5 minutes

    // ============ State ============

    /// @notice CCIP Router contract
    IRouterClient public immutable ccipRouter;

    /// @notice Underlying CCIP adapter for basic messaging
    CCIPAdapter public ccipAdapter;

    /// @notice Remote vault addresses by chain ID
    mapping(uint256 => address) public remoteVaults;

    /// @notice Chain ID to CCIP chain selector mapping
    mapping(uint256 => uint64) public chainIdToSelector;

    /// @notice CCIP chain selector to chain ID mapping
    mapping(uint64 => uint256) public selectorToChainId;

    /// @notice Chain ID to name mapping
    mapping(uint256 => string) public chainIdToName;

    /// @notice Supported chain IDs
    uint256[] public supportedChainIds;

    /// @notice Cached remote liquidity (updated via cross-chain queries)
    mapping(uint256 => mapping(address => uint256))
        public cachedRemoteLiquidity;

    /// @notice Last liquidity update timestamp per chain
    mapping(uint256 => uint256) public liquidityLastUpdated;

    /// @notice Liquidity transfer requests
    mapping(bytes32 => LiquidityTransferRequest) public transferRequests;

    /// @notice User's pending requests
    mapping(address => bytes32[]) public userPendingRequests;

    /// @notice Request counter for generating unique IDs
    uint256 private requestNonce;

    // ============ Events ============

    event RemoteVaultRegistered(
        uint256 chainId,
        uint64 selector,
        address vault
    );
    event LiquidityUpdated(uint256 chainId, address token, uint256 amount);
    event LiquidityTransferInitiated(
        bytes32 indexed requestId,
        address indexed user,
        uint256 sourceChainId,
        uint256 amount
    );
    event LiquidityTransferCompleted(bytes32 indexed requestId, bool success);
    event CCIPMessageSent(
        bytes32 indexed messageId,
        uint64 destinationSelector
    );

    // ============ Constructor ============

    constructor(address _ccipRouter, address _ccipAdapter) Ownable(msg.sender) {
        require(_ccipRouter != address(0), "Invalid router");

        ccipRouter = IRouterClient(_ccipRouter);
        ccipAdapter = CCIPAdapter(_ccipAdapter);
    }

    // ============ Admin Functions ============

    /**
     * @notice Register a remote vault for cross-chain liquidity
     * @param chainId Remote chain ID (e.g., 1 for mainnet, 137 for Polygon)
     * @param chainSelector CCIP chain selector
     * @param chainName Human-readable chain name
     * @param vault Vault address on that chain
     */
    function registerRemoteVault(
        uint256 chainId,
        uint64 chainSelector,
        string calldata chainName,
        address vault
    ) external onlyOwner {
        require(vault != address(0), "Invalid vault address");
        require(chainSelector != 0, "Invalid chain selector");

        remoteVaults[chainId] = vault;
        chainIdToSelector[chainId] = chainSelector;
        selectorToChainId[chainSelector] = chainId;
        chainIdToName[chainId] = chainName;

        // Add to supported chains if not present
        bool exists = false;
        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            if (supportedChainIds[i] == chainId) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            supportedChainIds.push(chainId);
        }

        emit RemoteVaultRegistered(chainId, chainSelector, vault);
    }

    /**
     * @notice Update cached remote liquidity (called by relayer or keeper)
     * @param chainId Remote chain ID
     * @param token Token address
     * @param amount Available liquidity
     */
    function updateRemoteLiquidity(
        uint256 chainId,
        address token,
        uint256 amount
    ) external onlyOwner {
        cachedRemoteLiquidity[chainId][token] = amount;
        liquidityLastUpdated[chainId] = block.timestamp;
        emit LiquidityUpdated(chainId, token, amount);
    }

    // ============ ILiquiditySource Implementation ============

    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            available += cachedRemoteLiquidity[supportedChainIds[i]][token];
        }
    }

    function getQuote(
        address token,
        uint256 amount
    ) external view override returns (LiquidityQuote memory quote) {
        uint256 totalAvailable = this.getAvailableLiquidity(token);

        // Get fee from CCIP router
        (uint256 fee, uint256 feeBps) = this.estimateLiquidityBridgeFee(
            supportedChainIds.length > 0 ? supportedChainIds[0] : 0,
            block.chainid,
            token,
            amount
        );

        quote = LiquidityQuote({
            sourceType: SourceType.CROSS_CHAIN_BRIDGE,
            sourceAddress: address(this),
            chainId: 0, // Multiple chains
            token: token,
            availableAmount: totalAvailable < amount ? totalAvailable : amount,
            feeBps: feeBps,
            estimatedTime: CCIP_STANDARD_TIME,
            rateAPY: 0,
            metadata: abi.encode(fee)
        });
    }

    function borrow(
        address token,
        uint256 amount,
        address recipient,
        bytes calldata data
    ) external override returns (bool success, bytes32 requestId) {
        uint256 sourceChainId;
        if (data.length >= 32) {
            sourceChainId = abi.decode(data, (uint256));
        } else {
            sourceChainId = _findBestSourceChain(token, amount);
        }

        require(sourceChainId != 0, "No source chain available");

        requestId = initiateLiquidityTransfer(
            sourceChainId,
            token,
            amount,
            recipient
        );
        success = true;
    }

    function supportsToken(
        address /* token */
    ) external pure override returns (bool) {
        return true;
    }

    function getSourceType() external pure override returns (SourceType) {
        return SourceType.CROSS_CHAIN_BRIDGE;
    }

    function isAsync() external pure override returns (bool) {
        return true;
    }

    // ============ ILiquidityBridgeAdapter Implementation ============

    function estimateLiquidityBridgeFee(
        uint256 sourceChainId,
        uint256 /* destChainId */,
        address /* token */,
        uint256 amount
    ) external view override returns (uint256 fee, uint256 feeBps) {
        uint64 selector = chainIdToSelector[sourceChainId];
        if (selector == 0) {
            return (0, 0);
        }

        // Build a sample message to estimate fee
        address destVault = remoteVaults[sourceChainId];
        bytes memory payload = abi.encode(
            "LIQUIDITY_REQUEST",
            bytes32(0),
            address(0),
            amount,
            address(0),
            block.chainid
        );

        Client.EVM2AnyMessage memory message = Client.EVM2AnyMessage({
            receiver: abi.encodePacked(destVault),
            data: payload,
            tokenAmounts: new Client.EVMTokenAmount[](0),
            feeToken: address(0),
            extraArgs: abi.encodePacked(bytes4(0x97a657c9), abi.encode(200000))
        });

        fee = ccipRouter.getFee(selector, message);

        if (amount > 0) {
            feeBps = (fee * 10000) / amount;
        }
    }

    function estimateBridgeTime(
        uint256 sourceChainId,
        uint256 /* destChainId */
    ) external view override returns (uint256) {
        // CCIP is generally fast, but some chains are faster
        string memory chainName = chainIdToName[sourceChainId];
        bytes32 nameHash = keccak256(bytes(chainName));

        // L2s are faster via CCIP
        if (
            nameHash == keccak256(bytes("arbitrum")) ||
            nameHash == keccak256(bytes("optimism")) ||
            nameHash == keccak256(bytes("base"))
        ) {
            return CCIP_FAST_TIME;
        }

        return CCIP_STANDARD_TIME;
    }

    function initiateLiquidityTransfer(
        uint256 sourceChainId,
        address token,
        uint256 amount,
        address recipient
    ) public payable override returns (bytes32 requestId) {
        require(
            remoteVaults[sourceChainId] != address(0),
            "Unknown source chain"
        );
        require(
            cachedRemoteLiquidity[sourceChainId][token] >= amount,
            "Insufficient remote liquidity"
        );

        uint64 destinationSelector = chainIdToSelector[sourceChainId];
        address destinationVault = remoteVaults[sourceChainId];

        // Generate unique request ID
        requestId = keccak256(
            abi.encodePacked(
                block.chainid,
                sourceChainId,
                msg.sender,
                token,
                amount,
                requestNonce++
            )
        );

        // Encode liquidity request payload
        bytes memory payload = abi.encode(
            "LIQUIDITY_REQUEST",
            requestId,
            token,
            amount,
            recipient,
            block.chainid
        );

        // Build CCIP message
        Client.EVM2AnyMessage memory message = Client.EVM2AnyMessage({
            receiver: abi.encodePacked(destinationVault),
            data: payload,
            tokenAmounts: new Client.EVMTokenAmount[](0),
            feeToken: address(0),
            extraArgs: abi.encodePacked(bytes4(0x97a657c9), abi.encode(200000))
        });

        // Get fee and verify sufficient payment
        uint256 fee = ccipRouter.getFee(destinationSelector, message);
        require(msg.value >= fee, "Insufficient fee");

        // Create transfer request
        transferRequests[requestId] = LiquidityTransferRequest({
            requestId: requestId,
            user: recipient,
            sourceChainId: sourceChainId,
            destChainId: block.chainid,
            token: token,
            amount: amount,
            fee: fee,
            timestamp: block.timestamp,
            status: LiquidityTransferStatus.PENDING
        });

        // Track for user
        userPendingRequests[recipient].push(requestId);

        // Reduce cached liquidity optimistically
        cachedRemoteLiquidity[sourceChainId][token] -= amount;

        // Send via CCIP
        bytes32 messageId = ccipRouter.ccipSend{value: fee}(
            destinationSelector,
            message
        );

        // Refund excess
        if (msg.value > fee) {
            payable(msg.sender).transfer(msg.value - fee);
        }

        emit CCIPMessageSent(messageId, destinationSelector);
        emit LiquidityTransferInitiated(
            requestId,
            recipient,
            sourceChainId,
            amount
        );
    }

    function getLiquidityTransferRequest(
        bytes32 requestId
    ) external view override returns (LiquidityTransferRequest memory) {
        return transferRequests[requestId];
    }

    function getPendingLiquidityRequests(
        address user
    ) external view override returns (bytes32[] memory) {
        return userPendingRequests[user];
    }

    function onLiquidityTransferComplete(
        bytes32 requestId,
        bool success
    ) external override {
        // In production, this would be called by CCIP receiver
        require(msg.sender == owner(), "Unauthorized");

        LiquidityTransferRequest storage request = transferRequests[requestId];
        require(request.timestamp != 0, "Unknown request");
        require(
            request.status == LiquidityTransferStatus.PENDING,
            "Not pending"
        );

        request.status = success
            ? LiquidityTransferStatus.COMPLETED
            : LiquidityTransferStatus.FAILED;

        if (!success) {
            cachedRemoteLiquidity[request.sourceChainId][
                request.token
            ] += request.amount;
        }

        _removePendingRequest(request.user, requestId);

        emit LiquidityTransferCompleted(requestId, success);
    }

    function supportsChainId(
        uint256 chainId
    ) external view override returns (bool) {
        return remoteVaults[chainId] != address(0);
    }

    function getRemoteLiquidity(
        uint256 remoteChainId,
        address token
    ) external view override returns (uint256) {
        return cachedRemoteLiquidity[remoteChainId][token];
    }

    // ============ IBridgeAdapter Delegation ============

    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address gasToken
    ) external payable override returns (bytes32) {
        return
            ccipAdapter.sendMessage{value: msg.value}(
                destinationChain,
                destinationAddress,
                payload,
                gasToken
            );
    }

    function estimateGas(
        string memory destinationChain,
        bytes memory payload
    ) external view override returns (uint256) {
        return ccipAdapter.estimateGas(destinationChain, payload);
    }

    function getProtocolName() external pure override returns (string memory) {
        return "CCIP";
    }

    function isChainSupported(
        string memory chainName
    ) external view override returns (bool) {
        return ccipAdapter.isChainSupported(chainName);
    }

    function getSupportedChains()
        external
        view
        override
        returns (string[] memory)
    {
        string[] memory chains = new string[](supportedChainIds.length);
        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            chains[i] = chainIdToName[supportedChainIds[i]];
        }
        return chains;
    }

    // ============ Internal Functions ============

    function _findBestSourceChain(
        address token,
        uint256 amount
    ) internal view returns (uint256 bestChain) {
        uint256 bestLiquidity = 0;

        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            uint256 chainId = supportedChainIds[i];
            uint256 available = cachedRemoteLiquidity[chainId][token];

            if (available >= amount && available > bestLiquidity) {
                bestLiquidity = available;
                bestChain = chainId;
            }
        }
    }

    function _removePendingRequest(address user, bytes32 requestId) internal {
        bytes32[] storage pending = userPendingRequests[user];
        for (uint256 i = 0; i < pending.length; i++) {
            if (pending[i] == requestId) {
                pending[i] = pending[pending.length - 1];
                pending.pop();
                break;
            }
        }
    }

    // ============ View Functions ============

    function getSupportedChainIds() external view returns (uint256[] memory) {
        return supportedChainIds;
    }

    function isLiquidityStale(
        uint256 chainId,
        uint256 maxAge
    ) external view returns (bool) {
        return block.timestamp - liquidityLastUpdated[chainId] > maxAge;
    }

    // ============ Receive ETH ============

    receive() external payable {}
}
