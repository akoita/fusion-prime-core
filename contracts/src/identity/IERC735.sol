// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IERC735
 * @dev Interface for ERC-735 Claim Holder
 * @notice This interface defines the standard for managing claims in a decentralized identity
 */
interface IERC735 {
    /**
     * @dev Claim structure
     */
    struct Claim {
        uint256 topic;
        uint256 scheme;
        address issuer;
        bytes signature;
        bytes data;
        string uri;
    }

    /**
     * @dev Claim topic constants
     */

    /**
     * @dev Signature scheme constants
     */

    /**
     * @dev Emitted when a claim is added
     * @param claimId The claim ID
     * @param topic The claim topic
     * @param scheme The signature scheme
     * @param issuer The claim issuer
     * @param signature The claim signature
     * @param data The claim data
     * @param uri The claim URI
     */
    event ClaimAdded(
        bytes32 indexed claimId,
        uint256 indexed topic,
        uint256 scheme,
        address indexed issuer,
        bytes signature,
        bytes data,
        string uri
    );

    /**
     * @dev Emitted when a claim is removed
     * @param claimId The claim ID
     * @param topic The claim topic
     * @param scheme The signature scheme
     * @param issuer The claim issuer
     * @param signature The claim signature
     * @param data The claim data
     * @param uri The claim URI
     */
    event ClaimRemoved(
        bytes32 indexed claimId,
        uint256 indexed topic,
        uint256 scheme,
        address indexed issuer,
        bytes signature,
        bytes data,
        string uri
    );

    /**
     * @dev Emitted when a claim is changed
     * @param claimId The claim ID
     * @param topic The claim topic
     * @param scheme The signature scheme
     * @param issuer The claim issuer
     * @param signature The claim signature
     * @param data The claim data
     * @param uri The claim URI
     */
    event ClaimChanged(
        bytes32 indexed claimId,
        uint256 indexed topic,
        uint256 scheme,
        address indexed issuer,
        bytes signature,
        bytes data,
        string uri
    );

    /**
     * @dev Emitted when a claim is requested
     * @param claimRequestId The claim request ID
     * @param topic The claim topic
     * @param scheme The signature scheme
     * @param issuer The claim issuer
     * @param signature The claim signature
     * @param data The claim data
     * @param uri The claim URI
     */
    event ClaimRequested(
        uint256 indexed claimRequestId,
        uint256 indexed topic,
        uint256 scheme,
        address indexed issuer,
        bytes signature,
        bytes data,
        string uri
    );

    /**
     * @dev Get a claim by ID
     * @param _claimId The claim ID
     * @return topic The claim topic
     * @return scheme The signature scheme
     * @return issuer The claim issuer
     * @return signature The claim signature
     * @return data The claim data
     * @return uri The claim URI
     */
    function getClaim(bytes32 _claimId)
        external
        view
        returns (uint256 topic, uint256 scheme, address issuer, bytes memory signature, bytes memory data, string memory uri);

    /**
     * @dev Get claims by topic
     * @param _topic The topic to filter by
     * @return claimIds Array of claim IDs
     */
    function getClaimIdsByTopic(uint256 _topic) external view returns (bytes32[] memory claimIds);

    /**
     * @dev Add a claim
     * @param _topic The claim topic
     * @param _scheme The signature scheme
     * @param _issuer The claim issuer
     * @param _signature The claim signature
     * @param _data The claim data
     * @param _uri The claim URI
     * @return claimRequestId The claim request ID
     */
    function addClaim(
        uint256 _topic,
        uint256 _scheme,
        address _issuer,
        bytes calldata _signature,
        bytes calldata _data,
        string calldata _uri
    ) external returns (bytes32 claimRequestId);

    /**
     * @dev Remove a claim
     * @param _claimId The claim ID to remove
     * @return success Whether the removal was successful
     */
    function removeClaim(bytes32 _claimId) external returns (bool success);
}
