// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

/**
 * @title IFlashLoanReceiver
 * @notice Interface for flash loan receiver contracts
 * @dev Implement this interface to receive flash loans from CrossChainVaultV30
 */
interface IFlashLoanReceiver {
    /**
     * @notice Called by the vault after flash loan tokens are sent
     * @param token The token address that was borrowed
     * @param amount The amount that was borrowed
     * @param fee The fee that must be repaid on top of the amount
     * @param initiator The address that initiated the flash loan
     * @param data Arbitrary data passed from the flash loan call
     * @return success True if the operation succeeded, must return true or the loan reverts
     */
    function executeOperation(address token, uint256 amount, uint256 fee, address initiator, bytes calldata data)
        external
        returns (bool success);
}
