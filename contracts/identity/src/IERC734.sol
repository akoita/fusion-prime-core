// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IERC734
 * @dev Interface for ERC-734 Key Management
 * @notice This interface defines the standard for managing keys in a decentralized identity
 */
interface IERC734 {
    /**
     * @dev Key purpose constants
     */

    /**
     * @dev Key structure
     */
    struct Key {
        uint256 purpose;
        uint256 keyType;
        bytes32 key;
    }

    /**
     * @dev Emitted when a key is added
     * @param key The key that was added
     * @param purpose The purpose of the key
     * @param keyType The type of key (1 = ECDSA, 2 = RSA, etc.)
     */
    event KeyAdded(bytes32 indexed key, uint256 indexed purpose, uint256 indexed keyType);

    /**
     * @dev Emitted when a key is removed
     * @param key The key that was removed
     * @param purpose The purpose of the key
     * @param keyType The type of key
     */
    event KeyRemoved(bytes32 indexed key, uint256 indexed purpose, uint256 indexed keyType);

    /**
     * @dev Emitted when an execution is requested
     * @param executionId The execution ID
     * @param to The target address
     * @param value The value to send
     * @param data The data to execute
     */
    event ExecutionRequested(uint256 indexed executionId, address indexed to, uint256 indexed value, bytes data);

    /**
     * @dev Emitted when an execution is executed
     * @param executionId The execution ID
     * @param to The target address
     * @param value The value sent
     * @param data The call data
     */
    event Executed(uint256 indexed executionId, address indexed to, uint256 indexed value, bytes data);

    /**
     * @dev Emitted when an execution is approved
     * @param executionId The execution ID
     * @param approved Whether it was approved
     */
    event Approved(uint256 indexed executionId, bool approved);

    /**
     * @dev Get a key by hash
     * @param _key The key hash
     * @return purpose The purpose of the key
     * @return keyType The type of the key
     * @return key The key itself
     */
    function getKey(bytes32 _key) external view returns (uint256 purpose, uint256 keyType, bytes32 key);

    /**
     * @dev Check if a key has a specific purpose
     * @param _key The key hash
     * @param _purpose The purpose to check
     * @return exists Whether the key exists with that purpose
     */
    function keyHasPurpose(bytes32 _key, uint256 _purpose) external view returns (bool exists);

    /**
     * @dev Get keys by purpose
     * @param _purpose The purpose to filter by
     * @return keys Array of key hashes
     */
    function getKeysByPurpose(uint256 _purpose) external view returns (bytes32[] memory keys);

    /**
     * @dev Add a key
     * @param _key The key to add
     * @param _purpose The purpose of the key
     * @param _keyType The type of the key
     * @return success Whether the addition was successful
     */
    function addKey(bytes32 _key, uint256 _purpose, uint256 _keyType) external returns (bool success);

    /**
     * @dev Remove a key
     * @param _key The key to remove
     * @param _purpose The purpose of the key
     * @return success Whether the removal was successful
     */
    function removeKey(bytes32 _key, uint256 _purpose) external returns (bool success);

    /**
     * @dev Execute an action
     * @param _to The target address
     * @param _value The value to send
     * @param _data The data to execute
     * @return executionId The execution ID
     */
    function execute(address _to, uint256 _value, bytes calldata _data) external payable returns (uint256 executionId);

    /**
     * @dev Approve an execution
     * @param _id The execution ID
     * @param _approve Whether to approve
     * @return success Whether the approval was successful
     */
    function approve(uint256 _id, bool _approve) external returns (bool success);
}
