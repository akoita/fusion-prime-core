// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "../interfaces/ILiquidityBridgeAdapter.sol";
import "./MessageBridgeAdapter.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MessageBridgeLiquidityAdapter
 * @notice Liquidity-focused extension of MessageBridgeAdapter for cross-chain borrowing
 * @dev Wraps the existing MessageBridgeAdapter with ILiquiditySource and ILiquidityBridgeAdapter
 *
 * Used for local/testnet development before deploying with production bridges (Axelar/CCIP).
 */
contract MessageBridgeLiquidityAdapter is
    ILiquiditySource,
    ILiquidityBridgeAdapter,
    Ownable
{
    // ============ Constants ============

    address public constant NATIVE_ETH = address(0);

    // Simulated bridge time for local testing (adjustable)
    uint256 public bridgeTimeSeconds = 10; // 10 seconds for local testing

    // Simulated bridge fee (adjustable, in basis points)
    uint256 public bridgeFeeBps = 10; // 0.1% for local testing

    // ============ State ============

    /// @notice The underlying message bridge adapter
    MessageBridgeAdapter public messageBridge;

    /// @notice Remote vault addresses by chain ID
    mapping(uint256 => address) public remoteVaults;

    /// @notice Simulated remote liquidity by chain ID and token
    mapping(uint256 => mapping(address => uint256))
        public simulatedRemoteLiquidity;

    /// @notice Supported chain IDs
    uint256[] public supportedChainIds;

    /// @notice Liquidity transfer requests
    mapping(bytes32 => LiquidityTransferRequest) public transferRequests;

    /// @notice User's pending requests
    mapping(address => bytes32[]) public userPendingRequests;

    /// @notice Request counter for generating unique IDs
    uint256 private requestNonce;

    // ============ Events ============

    event RemoteVaultRegistered(uint256 chainId, address vault);
    event SimulatedLiquiditySet(uint256 chainId, address token, uint256 amount);
    event LiquidityTransferInitiated(
        bytes32 indexed requestId,
        address indexed user,
        uint256 sourceChainId,
        uint256 amount
    );
    event LiquidityTransferCompleted(bytes32 indexed requestId, bool success);

    // ============ Constructor ============

    constructor(address _messageBridge) Ownable(msg.sender) {
        require(_messageBridge != address(0), "Invalid bridge address");
        messageBridge = MessageBridgeAdapter(_messageBridge);
    }

    // ============ Admin Functions ============

    /**
     * @notice Register a remote vault for cross-chain liquidity
     * @param chainId Remote chain ID
     * @param vault Vault address on that chain
     */
    function registerRemoteVault(
        uint256 chainId,
        address vault
    ) external onlyOwner {
        require(vault != address(0), "Invalid vault address");
        remoteVaults[chainId] = vault;

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

        emit RemoteVaultRegistered(chainId, vault);
    }

    /**
     * @notice Set simulated remote liquidity for testing
     * @param chainId Remote chain ID
     * @param token Token address (address(0) for ETH)
     * @param amount Available liquidity
     */
    function setSimulatedLiquidity(
        uint256 chainId,
        address token,
        uint256 amount
    ) external onlyOwner {
        simulatedRemoteLiquidity[chainId][token] = amount;
        emit SimulatedLiquiditySet(chainId, token, amount);
    }

    /**
     * @notice Update simulated bridge parameters (for testing)
     * @param _bridgeTimeSeconds New bridge time in seconds
     * @param _bridgeFeeBps New bridge fee in basis points
     */
    function setBridgeParameters(
        uint256 _bridgeTimeSeconds,
        uint256 _bridgeFeeBps
    ) external onlyOwner {
        bridgeTimeSeconds = _bridgeTimeSeconds;
        bridgeFeeBps = _bridgeFeeBps;
    }

    // ============ ILiquiditySource Implementation ============

    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            available += simulatedRemoteLiquidity[supportedChainIds[i]][token];
        }
    }

    function getQuote(
        address token,
        uint256 amount
    ) external view override returns (LiquidityQuote memory quote) {
        uint256 totalAvailable = this.getAvailableLiquidity(token);

        quote = LiquidityQuote({
            sourceType: SourceType.CROSS_CHAIN_BRIDGE,
            sourceAddress: address(this),
            chainId: 0, // Multiple chains
            token: token,
            availableAmount: totalAvailable < amount ? totalAvailable : amount,
            feeBps: bridgeFeeBps,
            estimatedTime: bridgeTimeSeconds,
            rateAPY: 0,
            metadata: ""
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
        return true; // Support all tokens for local testing
    }

    function getSourceType() external pure override returns (SourceType) {
        return SourceType.CROSS_CHAIN_BRIDGE;
    }

    function isAsync() external pure override returns (bool) {
        return true; // Bridge transfers are async
    }

    // ============ ILiquidityBridgeAdapter Implementation ============

    function estimateLiquidityBridgeFee(
        uint256 /* sourceChainId */,
        uint256 /* destChainId */,
        address /* token */,
        uint256 amount
    ) external view override returns (uint256 fee, uint256 feeBps_) {
        feeBps_ = bridgeFeeBps;
        fee = (amount * bridgeFeeBps) / 10000;
    }

    function estimateBridgeTime(
        uint256 /* sourceChainId */,
        uint256 /* destChainId */
    ) external view override returns (uint256) {
        return bridgeTimeSeconds;
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
            simulatedRemoteLiquidity[sourceChainId][token] >= amount,
            "Insufficient remote liquidity"
        );

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

        // Calculate fee
        uint256 fee = (amount * bridgeFeeBps) / 10000;

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

        // Reduce simulated liquidity
        simulatedRemoteLiquidity[sourceChainId][token] -= amount;

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
        LiquidityTransferRequest storage request = transferRequests[requestId];
        require(request.timestamp != 0, "Unknown request");
        require(
            request.status == LiquidityTransferStatus.PENDING,
            "Not pending"
        );

        request.status = success
            ? LiquidityTransferStatus.COMPLETED
            : LiquidityTransferStatus.FAILED;

        // If failed, restore simulated liquidity
        if (!success) {
            simulatedRemoteLiquidity[request.sourceChainId][
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
        return simulatedRemoteLiquidity[remoteChainId][token];
    }

    // ============ IBridgeAdapter Delegation ============

    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address gasToken
    ) external payable override returns (bytes32) {
        return
            messageBridge.sendMessage{value: msg.value}(
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
        return messageBridge.estimateGas(destinationChain, payload);
    }

    function getProtocolName() external pure override returns (string memory) {
        return "MessageBridge-Liquidity";
    }

    function isChainSupported(
        string memory chainName
    ) external view override returns (bool) {
        return messageBridge.isChainSupported(chainName);
    }

    function getSupportedChains()
        external
        view
        override
        returns (string[] memory)
    {
        return messageBridge.getSupportedChains();
    }

    // ============ Internal Functions ============

    function _findBestSourceChain(
        address token,
        uint256 amount
    ) internal view returns (uint256 bestChain) {
        uint256 bestLiquidity = 0;

        for (uint256 i = 0; i < supportedChainIds.length; i++) {
            uint256 chainId = supportedChainIds[i];
            uint256 available = simulatedRemoteLiquidity[chainId][token];

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

    // ============ Receive ETH ============

    receive() external payable {}
}
