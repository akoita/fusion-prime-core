// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Identity.sol";
import "./IERC735.sol";

/**
 * @title ClaimIssuerRegistry
 * @dev Registry for trusted claim issuers and claim issuance
 * @notice This contract manages trusted issuers and issues claims to user identities
 */
contract ClaimIssuerRegistry {
    // Owner of the registry (e.g., governance or admin)
    address public owner;

    // Mapping of trusted issuer addresses
    mapping(address => IssuerInfo) public issuers;

    // Array of all issuer addresses
    address[] public issuerList;

    struct IssuerInfo {
        bool isTrusted;
        string name;
        uint256[] allowedTopics;
        uint256 addedAt;
    }

    /**
     * @dev Emitted when an issuer is added
     * @param issuer The issuer address
     * @param name The issuer name
     */
    event IssuerAdded(address indexed issuer, string name);

    /**
     * @dev Emitted when an issuer is removed
     * @param issuer The issuer address
     */
    event IssuerRemoved(address indexed issuer);

    /**
     * @dev Emitted when a claim is issued
     * @param identity The identity contract address
     * @param claimId The claim ID
     * @param topic The claim topic
     * @param issuer The issuer address
     */
    event ClaimIssued(address indexed identity, bytes32 indexed claimId, uint256 indexed topic, address issuer);

    /**
     * @dev Modifier to restrict to owner
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "ClaimIssuerRegistry: caller is not owner");
        _;
    }

    /**
     * @dev Modifier to restrict to trusted issuers
     */
    modifier onlyTrustedIssuer() {
        require(issuers[msg.sender].isTrusted, "ClaimIssuerRegistry: caller is not trusted issuer");
        _;
    }

    /**
     * @dev Constructor
     */
    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Add a trusted issuer
     * @param _issuer The issuer address
     * @param _name The issuer name
     * @param _allowedTopics Array of topics the issuer can issue claims for
     */
    function addIssuer(address _issuer, string calldata _name, uint256[] calldata _allowedTopics) external onlyOwner {
        require(_issuer != address(0), "ClaimIssuerRegistry: invalid issuer address");
        require(!issuers[_issuer].isTrusted, "ClaimIssuerRegistry: issuer already exists");

        issuers[_issuer] = IssuerInfo({
            isTrusted: true,
            name: _name,
            allowedTopics: _allowedTopics,
            addedAt: block.timestamp
        });

        issuerList.push(_issuer);

        emit IssuerAdded(_issuer, _name);
    }

    /**
     * @dev Remove a trusted issuer
     * @param _issuer The issuer address
     */
    function removeIssuer(address _issuer) external onlyOwner {
        require(issuers[_issuer].isTrusted, "ClaimIssuerRegistry: issuer does not exist");

        issuers[_issuer].isTrusted = false;

        // Remove from array
        for (uint256 i = 0; i < issuerList.length; i++) {
            if (issuerList[i] == _issuer) {
                issuerList[i] = issuerList[issuerList.length - 1];
                issuerList.pop();
                break;
            }
        }

        emit IssuerRemoved(_issuer);
    }

    /**
     * @dev Issue a claim to an identity
     * @param _identity The identity contract address
     * @param _topic The claim topic
     * @param _scheme The signature scheme
     * @param _data The claim data
     * @param _uri The claim URI
     */
    function issueClaim(address _identity, uint256 _topic, uint256 _scheme, bytes calldata _data, string calldata _uri)
        external
        onlyTrustedIssuer
        returns (bytes32)
    {
        require(_identity != address(0), "ClaimIssuerRegistry: invalid identity address");
        require(_isTopicAllowed(msg.sender, _topic), "ClaimIssuerRegistry: topic not allowed for issuer");

        // Create signature
        bytes32 dataHash = keccak256(_data);
        bytes memory signature = _signData(dataHash);

        // Add claim to identity
        Identity identity = Identity(payable(_identity));
        bytes32 claimId = identity.addClaim(_topic, _scheme, msg.sender, signature, _data, _uri);

        emit ClaimIssued(_identity, claimId, _topic, msg.sender);

        return claimId;
    }

    /**
     * @dev Batch issue claims to multiple identities
     * @param _identities Array of identity addresses
     * @param _topic The claim topic
     * @param _scheme The signature scheme
     * @param _data The claim data
     * @param _uri The claim URI
     */
    function batchIssueClaims(
        address[] calldata _identities,
        uint256 _topic,
        uint256 _scheme,
        bytes calldata _data,
        string calldata _uri
    ) external onlyTrustedIssuer {
        require(_isTopicAllowed(msg.sender, _topic), "ClaimIssuerRegistry: topic not allowed for issuer");

        bytes32 dataHash = keccak256(_data);
        bytes memory signature = _signData(dataHash);

        for (uint256 i = 0; i < _identities.length; i++) {
            if (_identities[i] != address(0)) {
                try Identity(payable(_identities[i])).addClaim(_topic, _scheme, msg.sender, signature, _data, _uri)
                returns (bytes32 claimId) {
                    emit ClaimIssued(_identities[i], claimId, _topic, msg.sender);
                } catch {
                    // Continue on error
                    continue;
                }
            }
        }
    }

    /**
     * @dev Check if an identity has a specific claim
     * @param _identity The identity address
     * @param _topic The claim topic
     * @return Whether the identity has the claim
     */
    function hasValidClaim(address _identity, uint256 _topic) external view returns (bool) {
        if (_identity == address(0)) {
            return false;
        }

        try Identity(payable(_identity)).hasClaim(_topic) returns (bool result) {
            return result;
        } catch {
            return false;
        }
    }

    /**
     * @dev Get all trusted issuers
     * @return Array of trusted issuer addresses
     */
    function getTrustedIssuers() external view returns (address[] memory) {
        return issuerList;
    }

    /**
     * @dev Get issuer information
     * @param _issuer The issuer address
     * @return isTrusted Whether the issuer is trusted
     * @return name The issuer name
     * @return allowedTopics The allowed topics
     */
    function getIssuerInfo(address _issuer)
        external
        view
        returns (bool isTrusted, string memory name, uint256[] memory allowedTopics)
    {
        IssuerInfo memory info = issuers[_issuer];
        return (info.isTrusted, info.name, info.allowedTopics);
    }

    /**
     * @dev Check if a topic is allowed for an issuer
     * @param _issuer The issuer address
     * @param _topic The topic to check
     * @return Whether the topic is allowed
     */
    function isTopicAllowed(address _issuer, uint256 _topic) external view returns (bool) {
        return _isTopicAllowed(_issuer, _topic);
    }

    /**
     * @dev Internal function to check if topic is allowed
     */
    function _isTopicAllowed(address _issuer, uint256 _topic) private view returns (bool) {
        uint256[] memory allowedTopics = issuers[_issuer].allowedTopics;

        // Empty array means all topics allowed
        if (allowedTopics.length == 0) {
            return true;
        }

        for (uint256 i = 0; i < allowedTopics.length; i++) {
            if (allowedTopics[i] == _topic) {
                return true;
            }
        }

        return false;
    }

    /**
     * @dev Internal function to create signature
     * @param _dataHash The hash to sign
     * @return The signature
     */
    function _signData(bytes32 _dataHash) private view returns (bytes memory) {
        // In a real implementation, this would use an off-chain signing service
        // For now, we return a placeholder that indicates the signature should be created off-chain
        // The actual signing will be done by the Identity Service backend

        // Return empty signature for now - will be replaced by backend service
        return abi.encodePacked(bytes32(0), bytes32(0), uint8(0));
    }

    /**
     * @dev Transfer ownership
     * @param _newOwner The new owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "ClaimIssuerRegistry: invalid new owner");
        owner = _newOwner;
    }
}
