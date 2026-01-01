// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IdentityConstants
 * @dev Constants for ERC-734 and ERC-735
 */
library IdentityConstants {
    // ERC-734 Key Purposes
    uint256 constant MANAGEMENT_KEY = 1;
    uint256 constant ACTION_KEY = 2;
    uint256 constant CLAIM_SIGNER_KEY = 3;
    uint256 constant ENCRYPTION_KEY = 4;

    // ERC-735 Claim Topics
    uint256 constant KYC_VERIFIED = 1;
    uint256 constant AML_CLEARED = 2;
    uint256 constant ACCREDITED_INVESTOR = 3;
    uint256 constant SANCTIONS_CLEARED = 4;
    uint256 constant COUNTRY_ALLOWED = 5;

    // ERC-735 Claim Schemes
    uint256 constant ECDSA_SCHEME = 1;
    uint256 constant RSA_SCHEME = 2;
}
