// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IdentityVerifier} from "identity/IdentityVerifier.sol";

/**
 * @title EscrowWithIdentity
 * @notice Enhanced escrow contract with identity verification requirements
 * @dev Requires payer and payee to have verified identity claims before release
 */
contract EscrowWithIdentity {
    // Identity system integration
    address public immutable identityFactory;
    uint256[] public requiredClaims;

    // Participants
    address public payer;
    address public payee;
    address public arbiter;

    // Escrow state
    uint256 public amount;
    uint256 public createdAt;
    uint256 public releaseTime;
    bool public released;
    bool public refunded;

    // Approval tracking
    mapping(address => bool) public approvals;
    uint8 public approvalsRequired;
    uint8 public approvalsCount;

    // Identity verification bypass (for arbiter emergency release)
    bool public identityBypassEnabled;

    /**
     * @dev Errors
     */
    error Unauthorized();
    error AlreadyApproved();
    error EscrowAlreadyReleased();
    error EscrowAlreadyRefunded();
    error TimelockNotExpired();
    error InsufficientApprovals();
    error TransferFailed();
    error InvalidConfiguration();
    error IdentityVerificationRequired();
    error ClaimVerificationFailed();

    /**
     * @dev Events
     */
    event EscrowCreated(
        address indexed payer,
        address indexed payee,
        uint256 amount,
        uint256 releaseTime,
        uint8 approvalsRequired,
        uint256[] requiredClaims
    );
    event EscrowReleased(
        address indexed payee,
        uint256 amount,
        uint256 timestamp
    );
    event EscrowRefunded(
        address indexed payer,
        uint256 amount,
        uint256 timestamp
    );
    event Approved(address indexed approver);
    event ArbiterChanged(
        address indexed oldArbiter,
        address indexed newArbiter
    );
    event IdentityBypassToggled(bool enabled);

    /**
     * @notice Create an escrow with identity verification
     * @param _payer Address of the payer
     * @param _payee Recipient of the funds
     * @param _releaseDelay Seconds to wait before release
     * @param _approvalsRequired Number of approvals needed (1-3)
     * @param _arbiter Optional arbiter address
     * @param _identityFactory Identity factory contract address
     * @param _requiredClaims Array of required claim topics
     */
    constructor(
        address _payer,
        address _payee,
        uint256 _releaseDelay,
        uint8 _approvalsRequired,
        address _arbiter,
        address _identityFactory,
        uint256[] memory _requiredClaims
    ) payable {
        if (msg.value == 0) revert InvalidConfiguration();
        if (_payer == address(0)) revert InvalidConfiguration();
        if (_payee == address(0)) revert InvalidConfiguration();
        if (_approvalsRequired < 1 || _approvalsRequired > 3)
            revert InvalidConfiguration();
        if (_approvalsRequired == 3 && _arbiter == address(0))
            revert InvalidConfiguration();
        if (_identityFactory == address(0)) revert InvalidConfiguration();

        // Verify payer and payee have identities
        if (!IdentityVerifier.hasIdentity(_identityFactory, _payer)) {
            revert IdentityVerificationRequired();
        }
        if (!IdentityVerifier.hasIdentity(_identityFactory, _payee)) {
            revert IdentityVerificationRequired();
        }

        // If claims required, verify both parties have them
        if (_requiredClaims.length > 0) {
            (, bool payerHasClaims) = IdentityVerifier.verifyMultipleClaims(
                _identityFactory,
                _payer,
                _requiredClaims
            );
            (, bool payeeHasClaims) = IdentityVerifier.verifyMultipleClaims(
                _identityFactory,
                _payee,
                _requiredClaims
            );

            if (!payerHasClaims || !payeeHasClaims) {
                revert ClaimVerificationFailed();
            }
        }

        payer = _payer;
        payee = _payee;
        arbiter = _arbiter;
        amount = msg.value;
        createdAt = block.timestamp;
        releaseTime = block.timestamp + _releaseDelay;
        approvalsRequired = _approvalsRequired;
        identityFactory = _identityFactory;
        requiredClaims = _requiredClaims;

        emit EscrowCreated(
            _payer,
            _payee,
            amount,
            releaseTime,
            _approvalsRequired,
            _requiredClaims
        );
    }

    /**
     * @notice Approve the escrow release
     */
    function approve() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (approvals[msg.sender]) revert AlreadyApproved();
        if (
            msg.sender != payer &&
            msg.sender != payee &&
            (arbiter == address(0) || msg.sender != arbiter)
        ) {
            revert Unauthorized();
        }

        // Verify identity still valid (unless bypass enabled)
        if (!identityBypassEnabled) {
            _verifyIdentity(msg.sender);
        }

        approvals[msg.sender] = true;
        approvalsCount++;

        emit Approved(msg.sender);

        // Auto-release if conditions met
        if (
            approvalsCount >= approvalsRequired &&
            block.timestamp >= releaseTime
        ) {
            _release();
        }
    }

    /**
     * @notice Manually trigger release after conditions are met
     */
    function release() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (block.timestamp < releaseTime) revert TimelockNotExpired();
        if (approvalsCount < approvalsRequired) revert InsufficientApprovals();

        _release();
    }

    /**
     * @notice Refund payer if release conditions not met after 30 days
     */
    function refund() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (msg.sender != payer) revert Unauthorized();
        if (block.timestamp < releaseTime + 30 days)
            revert TimelockNotExpired();

        refunded = true;
        emit EscrowRefunded(payer, amount, block.timestamp);

        (bool ok, ) = payer.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    /**
     * @notice Change arbiter
     */
    function changeArbiter(address newArbiter) external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (arbiter != address(0) && msg.sender != arbiter)
            revert Unauthorized();
        if (arbiter == address(0) && msg.sender != payer) revert Unauthorized();

        address oldArbiter = arbiter;
        arbiter = newArbiter;
        emit ArbiterChanged(oldArbiter, newArbiter);
    }

    /**
     * @notice Toggle identity verification bypass (arbiter only)
     * @dev Emergency function in case identity system has issues
     */
    function toggleIdentityBypass() external {
        if (msg.sender != arbiter) revert Unauthorized();

        identityBypassEnabled = !identityBypassEnabled;
        emit IdentityBypassToggled(identityBypassEnabled);
    }

    /**
     * @notice Internal release logic
     */
    function _release() internal {
        // Final identity verification before release (unless bypass enabled)
        if (!identityBypassEnabled) {
            _verifyIdentity(payer);
            _verifyIdentity(payee);
        }

        released = true;
        emit EscrowReleased(payee, amount, block.timestamp);

        (bool ok, ) = payee.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    /**
     * @notice Verify identity and claims for an address
     * @param _address The address to verify
     */
    function _verifyIdentity(address _address) internal view {
        // Check has identity
        if (!IdentityVerifier.hasIdentity(identityFactory, _address)) {
            revert IdentityVerificationRequired();
        }

        // Check required claims if any
        if (requiredClaims.length > 0) {
            (, bool hasClaims) = IdentityVerifier.verifyMultipleClaims(
                identityFactory,
                _address,
                requiredClaims
            );
            if (!hasClaims) {
                revert ClaimVerificationFailed();
            }
        }
    }

    /**
     * @notice Check if escrow is ready to be released
     */
    function canRelease() external view returns (bool) {
        if (released || refunded) return false;
        if (approvalsCount < approvalsRequired) return false;
        if (block.timestamp < releaseTime) return false;

        // Check identity requirements (unless bypass enabled)
        if (!identityBypassEnabled) {
            if (!IdentityVerifier.hasIdentity(identityFactory, payer))
                return false;
            if (!IdentityVerifier.hasIdentity(identityFactory, payee))
                return false;

            if (requiredClaims.length > 0) {
                (, bool payerHasClaims) = IdentityVerifier.verifyMultipleClaims(
                    identityFactory,
                    payer,
                    requiredClaims
                );
                (, bool payeeHasClaims) = IdentityVerifier.verifyMultipleClaims(
                    identityFactory,
                    payee,
                    requiredClaims
                );

                if (!payerHasClaims || !payeeHasClaims) return false;
            }
        }

        return true;
    }

    /**
     * @notice Get escrow status summary
     */
    function getStatus()
        external
        view
        returns (
            bool _released,
            bool _refunded,
            uint8 _approvalsCount,
            uint8 _approvalsRequired,
            uint256 _releaseTime,
            bool _canRelease,
            bool _identityBypassEnabled
        )
    {
        return (
            released,
            refunded,
            approvalsCount,
            approvalsRequired,
            releaseTime,
            this.canRelease(),
            identityBypassEnabled
        );
    }

    /**
     * @notice Get required claims
     */
    function getRequiredClaims() external view returns (uint256[] memory) {
        return requiredClaims;
    }

    /**
     * @notice Verify if an address meets identity requirements
     */
    function verifyAddress(
        address _address
    ) external view returns (bool hasIdentity, bool hasClaims) {
        hasIdentity = IdentityVerifier.hasIdentity(identityFactory, _address);

        if (requiredClaims.length > 0) {
            (, hasClaims) = IdentityVerifier.verifyMultipleClaims(
                identityFactory,
                _address,
                requiredClaims
            );
        } else {
            hasClaims = true; // No claims required
        }

        return (hasIdentity, hasClaims);
    }
}
