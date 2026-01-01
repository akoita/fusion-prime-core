// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Identity.sol";

/**
 * @title IdentityFactory
 * @dev Factory contract for deploying user Identity contracts
 * @notice This contract creates and tracks Identity contracts for users
 */
contract IdentityFactory {
    // Mapping from user address to their identity contract
    mapping(address => address) public identities;

    // Array of all created identities
    address[] public allIdentities;

    // Claim issuer registry address
    address public claimIssuerRegistry;

    /**
     * @dev Emitted when a new identity is created
     * @param owner The owner of the identity
     * @param identity The identity contract address
     */
    event IdentityCreated(address indexed owner, address indexed identity);

    /**
     * @dev Emitted when claim issuer registry is updated
     * @param oldRegistry The old registry address
     * @param newRegistry The new registry address
     */
    event ClaimIssuerRegistryUpdated(address indexed oldRegistry, address indexed newRegistry);

    /**
     * @dev Constructor
     * @param _claimIssuerRegistry The claim issuer registry address
     */
    constructor(address _claimIssuerRegistry) {
        claimIssuerRegistry = _claimIssuerRegistry;
    }

    /**
     * @dev Create a new identity contract for the sender
     * @return identity The address of the created identity
     */
    function createIdentity() external returns (address) {
        return _createIdentity(msg.sender);
    }

    /**
     * @dev Create a new identity contract for a specific address
     * @param _owner The owner of the identity
     * @return identity The address of the created identity
     */
    function createIdentityFor(address _owner) external returns (address) {
        return _createIdentity(_owner);
    }

    /**
     * @dev Internal function to create identity
     * @param _owner The owner address
     * @return identity The created identity address
     */
    function _createIdentity(address _owner) private returns (address) {
        require(_owner != address(0), "IdentityFactory: owner cannot be zero address");
        require(identities[_owner] == address(0), "IdentityFactory: identity already exists");

        // Deploy new identity contract
        Identity identity = new Identity(_owner);
        address identityAddress = address(identity);

        // Store mapping
        identities[_owner] = identityAddress;
        allIdentities.push(identityAddress);

        // If claim issuer registry exists, add it as trusted issuer
        if (claimIssuerRegistry != address(0)) {
            identity.addTrustedIssuer(claimIssuerRegistry);
        }

        emit IdentityCreated(_owner, identityAddress);

        return identityAddress;
    }

    /**
     * @dev Get identity for an address
     * @param _owner The owner address
     * @return The identity contract address (zero if doesn't exist)
     */
    function getIdentity(address _owner) external view returns (address) {
        return identities[_owner];
    }

    /**
     * @dev Check if an address has an identity
     * @param _owner The owner address
     * @return Whether the address has an identity
     */
    function hasIdentity(address _owner) external view returns (bool) {
        return identities[_owner] != address(0);
    }

    /**
     * @dev Get total number of identities created
     * @return The total count
     */
    function getIdentityCount() external view returns (uint256) {
        return allIdentities.length;
    }

    /**
     * @dev Update the claim issuer registry
     * @param _newRegistry The new registry address
     */
    function updateClaimIssuerRegistry(address _newRegistry) external {
        // In production, add access control here
        address oldRegistry = claimIssuerRegistry;
        claimIssuerRegistry = _newRegistry;

        emit ClaimIssuerRegistryUpdated(oldRegistry, _newRegistry);
    }

    /**
     * @dev Get all identities (paginated)
     * @param _offset The starting index
     * @param _limit The number of results to return
     * @return identityAddresses Array of identity addresses
     * @return total Total number of identities
     */
    function getIdentities(uint256 _offset, uint256 _limit)
        external
        view
        returns (address[] memory identityAddresses, uint256 total)
    {
        total = allIdentities.length;

        if (_offset >= total) {
            return (new address[](0), total);
        }

        uint256 end = _offset + _limit;
        if (end > total) {
            end = total;
        }

        uint256 size = end - _offset;
        identityAddresses = new address[](size);

        for (uint256 i = 0; i < size; i++) {
            identityAddresses[i] = allIdentities[_offset + i];
        }

        return (identityAddresses, total);
    }
}
