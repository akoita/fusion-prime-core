// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Identity.sol";
import "./IdentityFactory.sol";
import "./ClaimIssuerRegistry.sol";
import "./IdentityConstants.sol";

/**
 * @title IdentityVerifier
 * @dev Library for verifying identity claims in other contracts
 * @notice This library provides helper functions for identity and claim verification
 */
library IdentityVerifier {
    /**
     * @dev Verify that an address has a specific claim
     * @param _factory The identity factory address
     * @param _user The user address
     * @param _topic The claim topic to verify
     * @return hasIdentity Whether the user has an identity
     * @return hasClaim Whether the user has the required claim
     */
    function verifyClaim(address _factory, address _user, uint256 _topic)
        internal
        view
        returns (bool hasIdentity, bool hasClaim)
    {
        if (_factory == address(0) || _user == address(0)) {
            return (false, false);
        }

        IdentityFactory factory = IdentityFactory(_factory);
        address identityAddress = factory.getIdentity(_user);

        if (identityAddress == address(0)) {
            return (false, false);
        }

        Identity identity = Identity(payable(identityAddress));

        try identity.hasClaim(_topic) returns (bool result) {
            return (true, result);
        } catch {
            return (true, false);
        }
    }

    /**
     * @dev Verify multiple claims (user must have ALL claims)
     * @param _factory The identity factory address
     * @param _user The user address
     * @param _topics Array of claim topics to verify
     * @return hasIdentity Whether the user has an identity
     * @return hasAllClaims Whether the user has all required claims
     */
    function verifyMultipleClaims(address _factory, address _user, uint256[] memory _topics)
        internal
        view
        returns (bool hasIdentity, bool hasAllClaims)
    {
        if (_factory == address(0) || _user == address(0) || _topics.length == 0) {
            return (false, false);
        }

        IdentityFactory factory = IdentityFactory(_factory);
        address identityAddress = factory.getIdentity(_user);

        if (identityAddress == address(0)) {
            return (false, false);
        }

        Identity identity = Identity(payable(identityAddress));

        for (uint256 i = 0; i < _topics.length; i++) {
            try identity.hasClaim(_topics[i]) returns (bool result) {
                if (!result) {
                    return (true, false);
                }
            } catch {
                return (true, false);
            }
        }

        return (true, true);
    }

    /**
     * @dev Verify any of multiple claims (user must have AT LEAST ONE claim)
     * @param _factory The identity factory address
     * @param _user The user address
     * @param _topics Array of claim topics to verify
     * @return hasIdentity Whether the user has an identity
     * @return hasAnyClaim Whether the user has at least one required claim
     */
    function verifyAnyClaim(address _factory, address _user, uint256[] memory _topics)
        internal
        view
        returns (bool hasIdentity, bool hasAnyClaim)
    {
        if (_factory == address(0) || _user == address(0) || _topics.length == 0) {
            return (false, false);
        }

        IdentityFactory factory = IdentityFactory(_factory);
        address identityAddress = factory.getIdentity(_user);

        if (identityAddress == address(0)) {
            return (false, false);
        }

        Identity identity = Identity(payable(identityAddress));

        for (uint256 i = 0; i < _topics.length; i++) {
            try identity.hasClaim(_topics[i]) returns (bool result) {
                if (result) {
                    return (true, true);
                }
            } catch {
                continue;
            }
        }

        return (true, false);
    }

    /**
     * @dev Get identity address for a user
     * @param _factory The identity factory address
     * @param _user The user address
     * @return The identity contract address (zero if doesn't exist)
     */
    function getIdentityAddress(address _factory, address _user) internal view returns (address) {
        if (_factory == address(0) || _user == address(0)) {
            return address(0);
        }

        IdentityFactory factory = IdentityFactory(_factory);
        return factory.getIdentity(_user);
    }

    /**
     * @dev Check if user has identity
     * @param _factory The identity factory address
     * @param _user The user address
     * @return Whether the user has an identity
     */
    function hasIdentity(address _factory, address _user) internal view returns (bool) {
        return getIdentityAddress(_factory, _user) != address(0);
    }

    /**
     * @dev Verify KYC claim specifically
     * @param _factory The identity factory address
     * @param _user The user address
     * @return hasIdentity Whether user has identity
     * @return isKYCVerified Whether user has KYC claim
     */
    function verifyKYC(address _factory, address _user) internal view returns (bool hasIdentity, bool isKYCVerified) {
        return verifyClaim(_factory, _user, 1); // KYC_VERIFIED = 1
    }

    /**
     * @dev Require KYC verification
     * @param _factory The identity factory address
     * @param _user The user address
     */
    function requireKYC(address _factory, address _user) internal view {
        (, bool isKYCVerified) = verifyKYC(_factory, _user);
        require(isKYCVerified, "IdentityVerifier: KYC verification required");
    }

    /**
     * @dev Require specific claim
     * @param _factory The identity factory address
     * @param _user The user address
     * @param _topic The required claim topic
     * @param _errorMessage Custom error message
     */
    function requireClaim(address _factory, address _user, uint256 _topic, string memory _errorMessage) internal view {
        (, bool hasClaim) = verifyClaim(_factory, _user, _topic);
        require(hasClaim, _errorMessage);
    }
}
