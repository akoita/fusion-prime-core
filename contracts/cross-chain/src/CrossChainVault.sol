// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {CrossChainVaultBase} from "./CrossChainVaultBase.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {
    SafeERC20
} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title IERC735Minimal
 * @notice Minimal interface for ERC-735 identity claims
 */
interface IERC735Minimal {
    function getClaim(
        bytes32 claimId
    )
        external
        view
        returns (
            uint256 topic,
            uint256 scheme,
            address issuer,
            bytes memory signature,
            bytes memory data,
            string memory uri
        );

    function getClaimIdsByTopic(
        uint256 topic
    ) external view returns (bytes32[] memory claimIds);
}

/**
 * @title CrossChainVault
 * @notice Cross-chain vault with KYC/compliance gating
 * @dev Extends CrossChainVaultBase with identity verification via ERC-735 claims
 *
 * Features:
 * - All base features (variable/stable rates, flash loans, pause, reserves)
 * - KYC verification via ERC-735 identity contracts
 * - Configurable compliance modes (permissionless or whitelist)
 * - Multi-issuer support for trusted claim providers
 *
 * Claim Topics:
 * - 1: KYC_VERIFIED
 * - 2: AML_CLEARED
 * - 3: ACCREDITED_INVESTOR
 */
contract CrossChainVault is CrossChainVaultBase {
    using SafeERC20 for IERC20;
    // ========== COMPLIANCE STATE ==========

    // Compliance modes
    enum ComplianceMode {
        PERMISSIONLESS, // No KYC required (default)
        WHITELIST // KYC required for all operations
    }

    // Claim topics
    uint256 public constant KYC_VERIFIED = 1;
    uint256 public constant AML_CLEARED = 2;
    uint256 public constant ACCREDITED_INVESTOR = 3;

    // Current compliance mode
    ComplianceMode public complianceMode = ComplianceMode.PERMISSIONLESS;

    // User identity contracts
    mapping(address => address) public userIdentities;

    // Trusted claim issuers
    mapping(address => bool) public trustedIssuers;
    address[] public issuerList;

    // Required claim topics (default: just KYC_VERIFIED)
    uint256[] public requiredClaims;

    // Authorized adapters for borrowing on behalf of users
    mapping(address => bool) public authorizedAdapters;

    // ========== EVENTS ==========

    event IdentityRegistered(address indexed user, address indexed identity);
    event IdentityRemoved(address indexed user);
    event ComplianceModeChanged(ComplianceMode oldMode, ComplianceMode newMode);
    event TrustedIssuerAdded(address indexed issuer);
    event TrustedIssuerRemoved(address indexed issuer);
    event RequiredClaimAdded(uint256 indexed topic);
    event RequiredClaimRemoved(uint256 indexed topic);

    // ========== ERRORS ==========

    error KYCRequired();
    error IdentityNotRegistered();
    error InvalidIdentityContract();
    error ClaimNotFound();
    error IssuerNotTrusted();
    error AlreadyRegistered();

    // ========== CONSTRUCTOR ==========

    constructor(
        address _gateway,
        address _gasService,
        address _priceOracle,
        address _interestRateModel
    )
        CrossChainVaultBase(
            _gateway,
            _gasService,
            _priceOracle,
            _interestRateModel
        )
    {
        // Default: require KYC_VERIFIED claim
        requiredClaims.push(KYC_VERIFIED);
    }

    // ========== COMPLIANCE MODIFIER ==========

    /**
     * @notice Modifier to enforce KYC compliance
     * @dev Only enforced when complianceMode is WHITELIST
     */
    modifier onlyCompliant() {
        if (complianceMode == ComplianceMode.WHITELIST) {
            if (!isKYCVerified(msg.sender)) {
                revert KYCRequired();
            }
        }
        _;
    }

    // ========== IDENTITY FUNCTIONS ==========

    /**
     * @notice Register an ERC-735 identity contract for the caller
     * @param identityContract Address of the identity contract
     */
    function registerIdentity(address identityContract) external {
        if (identityContract == address(0)) revert InvalidIdentityContract();
        if (userIdentities[msg.sender] != address(0))
            revert AlreadyRegistered();

        // Verify it's a valid identity contract by checking if it has the getClaim function
        try
            IERC735Minimal(identityContract).getClaimIdsByTopic(KYC_VERIFIED)
        returns (bytes32[] memory) {
            userIdentities[msg.sender] = identityContract;
            emit IdentityRegistered(msg.sender, identityContract);
        } catch {
            revert InvalidIdentityContract();
        }
    }

    /**
     * @notice Update identity contract (allows changing to a new identity)
     * @param identityContract New identity contract address
     */
    function updateIdentity(address identityContract) external {
        if (identityContract == address(0)) revert InvalidIdentityContract();

        try
            IERC735Minimal(identityContract).getClaimIdsByTopic(KYC_VERIFIED)
        returns (bytes32[] memory) {
            address oldIdentity = userIdentities[msg.sender];
            userIdentities[msg.sender] = identityContract;

            if (oldIdentity == address(0)) {
                emit IdentityRegistered(msg.sender, identityContract);
            } else {
                emit IdentityRemoved(msg.sender);
                emit IdentityRegistered(msg.sender, identityContract);
            }
        } catch {
            revert InvalidIdentityContract();
        }
    }

    /**
     * @notice Remove identity registration
     */
    function removeIdentity() external {
        if (userIdentities[msg.sender] == address(0))
            revert IdentityNotRegistered();
        delete userIdentities[msg.sender];
        emit IdentityRemoved(msg.sender);
    }

    /**
     * @notice Check if a user has valid KYC verification
     * @param user Address to check
     * @return True if user has all required claims from trusted issuers, or if in PERMISSIONLESS mode
     */
    function isKYCVerified(address user) public view returns (bool) {
        // In permissionless mode, all users are allowed
        if (complianceMode == ComplianceMode.PERMISSIONLESS) {
            return true;
        }

        address identity = userIdentities[user];
        if (identity == address(0)) return false;

        // Check all required claims
        for (uint256 i = 0; i < requiredClaims.length; i++) {
            if (!hasValidClaim(identity, requiredClaims[i])) {
                return false;
            }
        }

        return true;
    }

    /**
     * @notice Check if an identity has a valid claim for a topic
     * @param identity Identity contract address
     * @param topic Claim topic to check
     * @return True if valid claim exists from trusted issuer
     */
    function hasValidClaim(
        address identity,
        uint256 topic
    ) public view returns (bool) {
        try IERC735Minimal(identity).getClaimIdsByTopic(topic) returns (
            bytes32[] memory claimIds
        ) {
            for (uint256 i = 0; i < claimIds.length; i++) {
                try IERC735Minimal(identity).getClaim(claimIds[i]) returns (
                    uint256,
                    uint256,
                    address issuer,
                    bytes memory,
                    bytes memory,
                    string memory
                ) {
                    if (trustedIssuers[issuer]) {
                        return true;
                    }
                } catch {
                    continue;
                }
            }
        } catch {
            return false;
        }
        return false;
    }

    /**
     * @notice Get user's KYC status details
     * @param user Address to check
     * @return hasIdentity Whether user has registered identity
     * @return isVerified Whether user passes all KYC checks
     * @return missingClaims Topics of missing/invalid claims
     */
    function getKYCStatus(
        address user
    )
        external
        view
        returns (
            bool hasIdentity,
            bool isVerified,
            uint256[] memory missingClaims
        )
    {
        address identity = userIdentities[user];
        hasIdentity = identity != address(0);

        if (!hasIdentity) {
            missingClaims = requiredClaims;
            return (false, false, missingClaims);
        }

        // Count missing claims
        uint256 missingCount = 0;
        for (uint256 i = 0; i < requiredClaims.length; i++) {
            if (!hasValidClaim(identity, requiredClaims[i])) {
                missingCount++;
            }
        }

        // Build missing claims array
        missingClaims = new uint256[](missingCount);
        uint256 index = 0;
        for (uint256 i = 0; i < requiredClaims.length; i++) {
            if (!hasValidClaim(identity, requiredClaims[i])) {
                missingClaims[index] = requiredClaims[i];
                index++;
            }
        }

        isVerified = missingCount == 0;
    }

    // ========== COMPLIANT OVERRIDES ==========

    /**
     * @notice Deposit native ETH as collateral (with compliance check)
     */
    function deposit()
        external
        payable
        override
        whenNotPaused
        onlyCompliant
        nonReentrant
    {
        require(msg.value > 0, "Must deposit > 0");
        positions[msg.sender].collateral += msg.value;
        positions[msg.sender].lastUpdate = block.timestamp;
        emit Deposit(msg.sender, address(0), msg.value);
    }

    /**
     * @notice Deposit ERC20 tokens as collateral (with compliance check)
     */
    function depositToken(
        address token,
        uint256 amount
    )
        external
        override
        whenNotPaused
        onlyCompliant
        nonReentrant
        onlySupportedToken(token)
    {
        require(amount > 0, "Must deposit > 0");
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        tokenCollateral[msg.sender][token].deposited += amount;
        tokenCollateral[msg.sender][token].lastUpdate = block.timestamp;
        totalDeposited[token] += amount;
        emit Deposit(msg.sender, token, amount);
    }

    /**
     * @notice Borrow ERC20 tokens (with compliance check)
     */
    function borrow(
        address token,
        uint256 amount
    )
        external
        override
        whenNotPaused
        onlyCompliant
        nonReentrant
        onlySupportedToken(token)
    {
        _borrow(token, amount, RateMode.VARIABLE);
    }

    /**
     * @notice Borrow with chosen rate mode (with compliance check)
     */
    function borrowWithMode(
        address token,
        uint256 amount,
        RateMode mode
    )
        external
        override
        whenNotPaused
        onlyCompliant
        nonReentrant
        onlySupportedToken(token)
    {
        _borrow(token, amount, mode);
    }

    // Note: withdraw, withdrawToken, and repay remain accessible even without KYC
    // This allows users to exit their positions even if KYC expires

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Set compliance mode (governance only)
     * @param mode New compliance mode
     */
    function setComplianceMode(ComplianceMode mode) external onlyOwner {
        ComplianceMode oldMode = complianceMode;
        complianceMode = mode;
        emit ComplianceModeChanged(oldMode, mode);
    }

    /**
     * @notice Add a trusted claim issuer
     * @param issuer Issuer address
     */
    function addTrustedIssuer(address issuer) external onlyOwner {
        require(issuer != address(0), "Invalid issuer");
        require(!trustedIssuers[issuer], "Already trusted");

        trustedIssuers[issuer] = true;
        issuerList.push(issuer);

        emit TrustedIssuerAdded(issuer);
    }

    /**
     * @notice Remove a trusted claim issuer
     * @param issuer Issuer address
     */
    function removeTrustedIssuer(address issuer) external onlyOwner {
        require(trustedIssuers[issuer], "Not trusted");

        trustedIssuers[issuer] = false;

        // Remove from array
        for (uint256 i = 0; i < issuerList.length; i++) {
            if (issuerList[i] == issuer) {
                issuerList[i] = issuerList[issuerList.length - 1];
                issuerList.pop();
                break;
            }
        }

        emit TrustedIssuerRemoved(issuer);
    }

    /**
     * @notice Authorize an adapter for borrowing on behalf of users
     * @param adapter Adapter address
     * @param authorized True to authorize, false to revoke
     */
    function setAdapterAuthorization(
        address adapter,
        bool authorized
    ) external onlyOwner {
        authorizedAdapters[adapter] = authorized;
    }

    /**
     * @notice Add a required claim topic
     * @param topic Claim topic to require
     */
    function addRequiredClaim(uint256 topic) external onlyOwner {
        // Check not already required
        for (uint256 i = 0; i < requiredClaims.length; i++) {
            require(requiredClaims[i] != topic, "Already required");
        }

        requiredClaims.push(topic);
        emit RequiredClaimAdded(topic);
    }

    /**
     * @notice Remove a required claim topic
     * @param topic Claim topic to remove
     */
    function removeRequiredClaim(uint256 topic) external onlyOwner {
        for (uint256 i = 0; i < requiredClaims.length; i++) {
            if (requiredClaims[i] == topic) {
                requiredClaims[i] = requiredClaims[requiredClaims.length - 1];
                requiredClaims.pop();
                emit RequiredClaimRemoved(topic);
                return;
            }
        }
        revert ClaimNotFound();
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Get all trusted issuers
     */
    function getTrustedIssuers() external view returns (address[] memory) {
        return issuerList;
    }

    /**
     * @notice Get all required claim topics
     */
    function getRequiredClaims() external view returns (uint256[] memory) {
        return requiredClaims;
    }

    /**
     * @notice Check if an address is a trusted issuer
     */
    function isTrustedIssuer(address issuer) external view returns (bool) {
        return trustedIssuers[issuer];
    }

    // ========== NATIVE ETH BORROWING ==========

    // Track ETH borrowed per user
    mapping(address => uint256) public ethBorrowed;
    uint256 public totalETHBorrowed;

    event BorrowETH(address indexed user, uint256 amount);
    event RepayETH(address indexed user, uint256 amount);
    error InsufficientETHLiquidity();
    error InsufficientCredit();
    error InsufficientETHDebt();

    /**
     * @notice Borrow native ETH against collateral
     * @param amount Amount of ETH to borrow
     */
    function borrowETH(
        uint256 amount
    ) external whenNotPaused nonReentrant onlyCompliant {
        require(amount > 0, "Must borrow > 0");

        // Check vault has enough ETH liquidity
        uint256 availableETH = address(this).balance;
        if (amount > availableETH) revert InsufficientETHLiquidity();

        // Update user's ETH debt
        ethBorrowed[msg.sender] += amount;
        totalETHBorrowed += amount;

        // Update position borrowed value (in USD via oracle)
        uint256 borrowValueUSD = priceOracle.convertTokenToUSD(
            address(0),
            amount
        );
        positions[msg.sender].borrowed += borrowValueUSD;
        positions[msg.sender].lastUpdate = block.timestamp;

        // Check health factor
        require(getHealthFactor(msg.sender) >= 100, "Undercollateralized");

        // Transfer ETH to borrower
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "ETH transfer failed");

        emit BorrowETH(msg.sender, amount);
    }

    /**
     * @notice Repay borrowed ETH
     */
    function repayETH() external payable nonReentrant {
        require(msg.value > 0, "Must repay > 0");

        uint256 debt = ethBorrowed[msg.sender];
        if (debt == 0) revert InsufficientETHDebt();

        uint256 repayAmount = msg.value > debt ? debt : msg.value;
        uint256 excess = msg.value - repayAmount;

        // Update debt
        ethBorrowed[msg.sender] -= repayAmount;
        totalETHBorrowed -= repayAmount;

        // Update position (reduce borrowed value)
        uint256 repayValueUSD = priceOracle.convertTokenToUSD(
            address(0),
            repayAmount
        );
        if (positions[msg.sender].borrowed >= repayValueUSD) {
            positions[msg.sender].borrowed -= repayValueUSD;
        } else {
            positions[msg.sender].borrowed = 0;
        }
        positions[msg.sender].lastUpdate = block.timestamp;

        // Return excess
        if (excess > 0) {
            (bool success, ) = payable(msg.sender).call{value: excess}("");
            require(success, "Excess refund failed");
        }

        emit RepayETH(msg.sender, repayAmount);
    }

    /**
     * @notice Get available ETH to borrow
     */
    function getAvailableETH() external view returns (uint256) {
        return
            address(this).balance > totalETHBorrowed
                ? address(this).balance - totalETHBorrowed
                : 0;
    }

    /**
     * @notice Borrow native ETH on behalf of a user
     * @param amount Amount to borrow
     * @param onBehalfOf User to assign debt to
     */
    function borrowETHFor(
        uint256 amount,
        address onBehalfOf
    ) external whenNotPaused nonReentrant {
        require(authorizedAdapters[msg.sender], "Not authorized");
        require(amount > 0, "Must borrow > 0");

        // Check user's compliance (public function in V31)
        require(isKYCVerified(onBehalfOf), "User not compliant");

        uint256 availableETH = address(this).balance;
        if (amount > availableETH) revert InsufficientETHLiquidity();

        ethBorrowed[onBehalfOf] += amount;
        totalETHBorrowed += amount;

        // Update position borrowed value (USD)
        uint256 borrowValueUSD = priceOracle.convertToUSD(amount);
        positions[onBehalfOf].borrowed += borrowValueUSD;
        positions[onBehalfOf].lastUpdate = block.timestamp;

        // Check health factor
        require(getHealthFactor(onBehalfOf) >= 100, "Undercollateralized");

        (bool success, ) = payable(onBehalfOf).call{value: amount}("");
        require(success, "Transfer failed");
        emit BorrowETH(onBehalfOf, amount);
    }

    /**
     * @notice Borrow ERC20 tokens on behalf of a user
     * @param token Token address
     * @param amount Amount to borrow
     * @param onBehalfOf User to assign debt to
     */
    function borrowFor(
        address token,
        uint256 amount,
        address onBehalfOf
    ) external whenNotPaused nonReentrant onlySupportedToken(token) {
        require(authorizedAdapters[msg.sender], "Not authorized");
        require(amount > 0, "Must borrow > 0");
        require(isKYCVerified(onBehalfOf), "User not compliant");
        require(
            totalDeposited[token] - totalBorrowed[token] >= amount,
            "Insufficient liquidity"
        );

        // Accrue interest first
        _accrueInterest(onBehalfOf, token);

        TokenCollateral storage tc = tokenCollateral[onBehalfOf][token];
        tc.borrowed += amount;
        tc.rateMode = RateMode.VARIABLE;
        tc.lastUpdate = block.timestamp;

        totalBorrowed[token] += amount;

        // Update position
        uint256 borrowValueUSD = priceOracle.convertTokenToUSD(token, amount);
        positions[onBehalfOf].borrowed += borrowValueUSD;
        positions[onBehalfOf].lastUpdate = block.timestamp;

        // Check health factor
        require(getHealthFactor(onBehalfOf) >= 100, "Undercollateralized");

        IERC20(token).safeTransfer(onBehalfOf, amount);

        emit Borrow(onBehalfOf, token, amount, RateMode.VARIABLE);
    }
}
