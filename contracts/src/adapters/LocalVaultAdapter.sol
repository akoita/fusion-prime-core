// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "lending/CrossChainVault.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title LocalVaultAdapter
 * @notice Adapter for the local CrossChainVault as a liquidity source
 * @dev Wraps CrossChainVault to implement ILiquiditySource interface
 *
 * This is the default liquidity source - always checked first, no fees, instant execution.
 */
contract LocalVaultAdapter is ILiquiditySource {
    /// @notice The local vault contract
    CrossChainVault public immutable vault;

    /// @notice Native ETH placeholder
    address public constant NATIVE_ETH = address(0);

    constructor(address _vault) {
        require(_vault != address(0), "Invalid vault address");
        vault = CrossChainVault(payable(_vault));
    }

    // ============ ILiquiditySource Implementation ============

    /**
     * @notice Get available ETH or token liquidity in the vault
     * @param token Token address (address(0) for native ETH)
     * @return available Amount available to borrow
     */
    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        if (token == NATIVE_ETH) {
            // For ETH, use the vault's getAvailableETH() function
            available = vault.getAvailableETH();
        } else {
            // For ERC20 tokens, check vault's balance minus any already borrowed
            uint256 vaultBalance = IERC20(token).balanceOf(address(vault));
            uint256 totalBorrowed = vault.totalBorrowed(token);
            available = vaultBalance > totalBorrowed
                ? vaultBalance - totalBorrowed
                : 0;
        }
    }

    /**
     * @notice Get a quote for borrowing from the local vault
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @return quote Full quote details (0 fees, instant)
     */
    function getQuote(
        address token,
        uint256 amount
    ) external view override returns (LiquidityQuote memory quote) {
        uint256 available = this.getAvailableLiquidity(token);

        quote = LiquidityQuote({
            sourceType: SourceType.LOCAL_VAULT,
            sourceAddress: address(vault),
            chainId: block.chainid,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: 0, // No fees for local vault
            estimatedTime: 0, // Instant execution
            rateAPY: 0, // No external rate (uses vault's internal rate)
            metadata: ""
        });
    }

    /**
     * @notice Execute a borrow from the local vault
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param recipient Address to receive funds
     * @param data Additional data (unused for local vault)
     * @return success Whether the borrow succeeded
     * @return requestId Empty for instant borrows
     */
    function borrow(
        address token,
        uint256 amount,
        address recipient,
        bytes calldata data
    ) external override returns (bool success, bytes32 requestId) {
        // Note: This adapter needs to be called by an authorized entity
        // The borrow is executed on behalf of the user

        if (token == NATIVE_ETH) {
            // Borrow native ETH using borrowETHFor
            vault.borrowETHFor(amount, recipient);
        } else {
            // Borrow ERC20 token using borrowFor(token, amount, recipient)
            vault.borrowFor(token, amount, recipient);
        }

        success = true;
        requestId = bytes32(0); // No async tracking needed
    }

    /**
     * @notice Check if the vault supports a token
     * @param token Token address
     * @return supported Whether the token is supported
     */
    function supportsToken(
        address token
    ) external view override returns (bool supported) {
        if (token == NATIVE_ETH) {
            return true; // Native ETH always supported
        }
        // Check if token is in supportedTokens
        return vault.supportedTokens(token);
    }

    /**
     * @notice Get the source type (LOCAL_VAULT)
     * @return sourceType Always returns LOCAL_VAULT
     */
    function getSourceType() external pure override returns (SourceType) {
        return SourceType.LOCAL_VAULT;
    }

    /**
     * @notice Check if borrows are async (they're not for local vault)
     * @return isAsync Always false for local vault
     */
    function isAsync() external pure override returns (bool) {
        return false; // Local borrows are instant
    }

    // ============ Receive ETH ============

    receive() external payable {}
}
