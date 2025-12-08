// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IERC734.sol";
import "./IERC735.sol";
import "./IdentityConstants.sol";

/**
 * @title Identity
 * @dev Implementation of ERC-734 (Key Management) and ERC-735 (Claim Holder)
 * @notice This contract represents a user's decentralized identity with key and claim management
 */
contract Identity is IERC734, IERC735 {
    using IdentityConstants for *;

    // Re-export constants for easier access
    uint256 public constant MANAGEMENT_KEY = IdentityConstants.MANAGEMENT_KEY;
    uint256 public constant ACTION_KEY = IdentityConstants.ACTION_KEY;
    uint256 public constant CLAIM_SIGNER_KEY = IdentityConstants.CLAIM_SIGNER_KEY;
    uint256 public constant ENCRYPTION_KEY = IdentityConstants.ENCRYPTION_KEY;
    uint256 public constant KYC_VERIFIED = IdentityConstants.KYC_VERIFIED;
    uint256 public constant AML_CLEARED = IdentityConstants.AML_CLEARED;
    uint256 public constant ACCREDITED_INVESTOR = IdentityConstants.ACCREDITED_INVESTOR;
    uint256 public constant SANCTIONS_CLEARED = IdentityConstants.SANCTIONS_CLEARED;
    uint256 public constant COUNTRY_ALLOWED = IdentityConstants.COUNTRY_ALLOWED;
    uint256 public constant ECDSA_SCHEME = IdentityConstants.ECDSA_SCHEME;
    uint256 public constant RSA_SCHEME = IdentityConstants.RSA_SCHEME;
    // Key storage
    mapping(bytes32 => Key) private keys;
    mapping(uint256 => bytes32[]) private keysByPurpose;
    mapping(bytes32 => uint256[]) private keyPurposes;

    // Claim storage
    mapping(bytes32 => Claim) private claims;
    mapping(uint256 => bytes32[]) private claimsByTopic;

    // Execution storage
    uint256 private executionNonce;
    mapping(uint256 => Execution) private executions;

    struct Execution {
        address to;
        uint256 value;
        bytes data;
        bool approved;
        bool executed;
    }

    // Trusted claim issuers (set by management keys)
    mapping(address => bool) public trustedIssuers;

    /**
     * @dev Modifier to restrict access to management keys
     */
    modifier onlyManagementKey() {
        bytes32 key = keccak256(abi.encodePacked(msg.sender));
        require(keyHasPurpose(key, MANAGEMENT_KEY), "Identity: sender is not management key");
        _;
    }

    /**
     * @dev Modifier to restrict access to action keys
     */
    modifier onlyActionKey() {
        bytes32 key = keccak256(abi.encodePacked(msg.sender));
        require(
            keyHasPurpose(key, ACTION_KEY) || keyHasPurpose(key, MANAGEMENT_KEY),
            "Identity: sender is not action or management key"
        );
        _;
    }

    /**
     * @dev Constructor - initializes identity with creator as management key
     * @param _owner The initial owner address
     */
    constructor(address _owner) {
        bytes32 ownerKey = keccak256(abi.encodePacked(_owner));

        // Add owner as management key
        keys[ownerKey] = Key({purpose: MANAGEMENT_KEY, keyType: 1, key: ownerKey});

        keysByPurpose[MANAGEMENT_KEY].push(ownerKey);
        keyPurposes[ownerKey].push(MANAGEMENT_KEY);

        emit KeyAdded(ownerKey, MANAGEMENT_KEY, 1);
    }

    // ============================================
    // ERC-734 Key Management Implementation
    // ============================================

    /**
     * @inheritdoc IERC734
     */
    function getKey(bytes32 _key) external view override returns (uint256 purpose, uint256 keyType, bytes32 key) {
        Key memory k = keys[_key];
        return (k.purpose, k.keyType, k.key);
    }

    /**
     * @inheritdoc IERC734
     */
    function keyHasPurpose(bytes32 _key, uint256 _purpose) public view override returns (bool) {
        if (keys[_key].key == 0) {
            return false;
        }

        uint256[] memory purposes = keyPurposes[_key];
        for (uint256 i = 0; i < purposes.length; i++) {
            if (purposes[i] == _purpose) {
                return true;
            }
        }
        return false;
    }

    /**
     * @inheritdoc IERC734
     */
    function getKeysByPurpose(uint256 _purpose) external view override returns (bytes32[] memory) {
        return keysByPurpose[_purpose];
    }

    /**
     * @inheritdoc IERC734
     */
    function addKey(bytes32 _key, uint256 _purpose, uint256 _keyType) external override onlyManagementKey returns (bool) {
        require(_key != 0, "Identity: key cannot be zero");
        require(_purpose != 0, "Identity: purpose cannot be zero");

        // If key doesn't exist, create it
        if (keys[_key].key == 0) {
            keys[_key] = Key({purpose: _purpose, keyType: _keyType, key: _key});
        }

        // Add purpose if not already present
        if (!keyHasPurpose(_key, _purpose)) {
            keyPurposes[_key].push(_purpose);
            keysByPurpose[_purpose].push(_key);
        }

        emit KeyAdded(_key, _purpose, _keyType);
        return true;
    }

    /**
     * @inheritdoc IERC734
     */
    function removeKey(bytes32 _key, uint256 _purpose) external override onlyManagementKey returns (bool) {
        require(keyHasPurpose(_key, _purpose), "Identity: key does not have this purpose");

        // Don't allow removing last management key
        if (_purpose == MANAGEMENT_KEY) {
            require(keysByPurpose[MANAGEMENT_KEY].length > 1, "Identity: cannot remove last management key");
        }

        // Remove purpose from key
        uint256[] storage purposes = keyPurposes[_key];
        for (uint256 i = 0; i < purposes.length; i++) {
            if (purposes[i] == _purpose) {
                purposes[i] = purposes[purposes.length - 1];
                purposes.pop();
                break;
            }
        }

        // Remove key from purpose list
        bytes32[] storage purposeKeys = keysByPurpose[_purpose];
        for (uint256 i = 0; i < purposeKeys.length; i++) {
            if (purposeKeys[i] == _key) {
                purposeKeys[i] = purposeKeys[purposeKeys.length - 1];
                purposeKeys.pop();
                break;
            }
        }

        emit KeyRemoved(_key, _purpose, keys[_key].keyType);
        return true;
    }

    /**
     * @inheritdoc IERC734
     */
    function execute(address _to, uint256 _value, bytes calldata _data)
        external
        payable
        override
        onlyActionKey
        returns (uint256)
    {
        uint256 executionId = executionNonce++;

        executions[executionId] = Execution({to: _to, value: _value, data: _data, approved: false, executed: false});

        emit ExecutionRequested(executionId, _to, _value, _data);

        // Auto-approve if sender is management key
        bytes32 senderKey = keccak256(abi.encodePacked(msg.sender));
        if (keyHasPurpose(senderKey, MANAGEMENT_KEY)) {
            approve(executionId, true);
        }

        return executionId;
    }

    /**
     * @inheritdoc IERC734
     */
    function approve(uint256 _id, bool _approve) public override onlyManagementKey returns (bool) {
        require(executions[_id].to != address(0), "Identity: execution does not exist");
        require(!executions[_id].executed, "Identity: execution already executed");

        executions[_id].approved = _approve;
        emit Approved(_id, _approve);

        if (_approve) {
            Execution storage exec = executions[_id];
            exec.executed = true;

            (bool success,) = exec.to.call{value: exec.value}(exec.data);
            require(success, "Identity: execution failed");

            emit Executed(_id, exec.to, exec.value, exec.data);
        }

        return true;
    }

    // ============================================
    // ERC-735 Claim Holder Implementation
    // ============================================

    /**
     * @inheritdoc IERC735
     */
    function getClaim(bytes32 _claimId)
        external
        view
        override
        returns (uint256 topic, uint256 scheme, address issuer, bytes memory signature, bytes memory data, string memory uri)
    {
        Claim memory claim = claims[_claimId];
        return (claim.topic, claim.scheme, claim.issuer, claim.signature, claim.data, claim.uri);
    }

    /**
     * @inheritdoc IERC735
     */
    function getClaimIdsByTopic(uint256 _topic) external view override returns (bytes32[] memory) {
        return claimsByTopic[_topic];
    }

    /**
     * @inheritdoc IERC735
     */
    function addClaim(
        uint256 _topic,
        uint256 _scheme,
        address _issuer,
        bytes calldata _signature,
        bytes calldata _data,
        string calldata _uri
    ) external override returns (bytes32) {
        bytes32 claimId = keccak256(abi.encodePacked(_issuer, _topic));

        // Verify signature if scheme is ECDSA
        if (_scheme == ECDSA_SCHEME) {
            bytes32 dataHash = keccak256(_data);
            address signer = _recoverSigner(dataHash, _signature);
            require(signer == _issuer, "Identity: invalid claim signature");
        }

        // Check if issuer is trusted or if claim is self-issued
        bytes32 senderKey = keccak256(abi.encodePacked(msg.sender));
        bool isSelfIssued = msg.sender == address(this) || keyHasPurpose(senderKey, CLAIM_SIGNER_KEY);

        require(trustedIssuers[_issuer] || isSelfIssued, "Identity: issuer not trusted");

        // Add or update claim
        bool isNew = claims[claimId].issuer == address(0);

        claims[claimId] = Claim({
            topic: _topic,
            scheme: _scheme,
            issuer: _issuer,
            signature: _signature,
            data: _data,
            uri: _uri
        });

        if (isNew) {
            claimsByTopic[_topic].push(claimId);
            emit ClaimAdded(claimId, _topic, _scheme, _issuer, _signature, _data, _uri);
        } else {
            emit ClaimChanged(claimId, _topic, _scheme, _issuer, _signature, _data, _uri);
        }

        return claimId;
    }

    /**
     * @inheritdoc IERC735
     */
    function removeClaim(bytes32 _claimId) external override returns (bool) {
        Claim memory claim = claims[_claimId];
        require(claim.issuer != address(0), "Identity: claim does not exist");

        // Only issuer or identity owner can remove claim
        bytes32 senderKey = keccak256(abi.encodePacked(msg.sender));
        require(
            msg.sender == claim.issuer || keyHasPurpose(senderKey, MANAGEMENT_KEY),
            "Identity: not authorized to remove claim"
        );

        // Remove claim from topic list
        bytes32[] storage topicClaims = claimsByTopic[claim.topic];
        for (uint256 i = 0; i < topicClaims.length; i++) {
            if (topicClaims[i] == _claimId) {
                topicClaims[i] = topicClaims[topicClaims.length - 1];
                topicClaims.pop();
                break;
            }
        }

        emit ClaimRemoved(_claimId, claim.topic, claim.scheme, claim.issuer, claim.signature, claim.data, claim.uri);

        delete claims[_claimId];
        return true;
    }

    // ============================================
    // Trusted Issuer Management
    // ============================================

    /**
     * @dev Add a trusted claim issuer
     * @param _issuer The issuer address to trust
     */
    function addTrustedIssuer(address _issuer) external onlyManagementKey {
        trustedIssuers[_issuer] = true;
    }

    /**
     * @dev Remove a trusted claim issuer
     * @param _issuer The issuer address to untrust
     */
    function removeTrustedIssuer(address _issuer) external onlyManagementKey {
        trustedIssuers[_issuer] = false;
    }

    // ============================================
    // Utility Functions
    // ============================================

    /**
     * @dev Recover signer from signature
     * @param _hash The hash that was signed
     * @param _signature The signature
     * @return The signer address
     */
    function _recoverSigner(bytes32 _hash, bytes memory _signature) private pure returns (address) {
        bytes32 r;
        bytes32 s;
        uint8 v;

        if (_signature.length != 65) {
            return address(0);
        }

        assembly {
            r := mload(add(_signature, 32))
            s := mload(add(_signature, 64))
            v := byte(0, mload(add(_signature, 96)))
        }

        if (v < 27) {
            v += 27;
        }

        if (v != 27 && v != 28) {
            return address(0);
        }

        return ecrecover(_hash, v, r, s);
    }

    /**
     * @dev Check if identity has a specific claim from a trusted issuer
     * @param _topic The claim topic
     * @return Whether the identity has the claim
     */
    function hasClaim(uint256 _topic) external view returns (bool) {
        bytes32[] memory claimIds = claimsByTopic[_topic];

        for (uint256 i = 0; i < claimIds.length; i++) {
            Claim memory claim = claims[claimIds[i]];
            if (trustedIssuers[claim.issuer]) {
                return true;
            }
        }

        return false;
    }

    /**
     * @dev Receive function to accept ETH
     */
    receive() external payable {}
}
