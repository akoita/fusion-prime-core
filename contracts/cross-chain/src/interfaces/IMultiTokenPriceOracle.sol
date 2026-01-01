// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IPriceOracle} from "./IPriceOracle.sol";

/**
 * @title IMultiTokenPriceOracle
 * @notice Extended interface for price oracles supporting multiple ERC20 tokens
 * @dev Used by CrossChainVaultV29 for multi-currency support
 */
interface IMultiTokenPriceOracle is IPriceOracle {
    /**
     * @notice Get price for a specific token in USD
     * @param token Token address
     * @return price Price in USD with 8 decimals
     */
    function getTokenPrice(address token) external view returns (uint256 price);

    /**
     * @notice Convert token amount to USD value
     * @param token Token address
     * @param amount Token amount (with token's decimals)
     * @return usdValue USD value with 18 decimals
     */
    function convertTokenToUSD(address token, uint256 amount) external view returns (uint256 usdValue);

    /**
     * @notice Convert USD value to token amount
     * @param token Token address
     * @param usdValue USD value with 18 decimals
     * @return amount Token amount (with token's decimals)
     */
    function convertUSDToToken(address token, uint256 usdValue) external view returns (uint256 amount);

    /**
     * @notice Check if a token is supported by this oracle
     * @param token Token address
     * @return supported True if token has a price feed
     */
    function isTokenSupported(address token) external view returns (bool supported);

    /**
     * @notice Get token decimals
     * @param token Token address
     * @return decimals Token decimals (e.g., 6 for USDC, 18 for WETH)
     */
    function getTokenDecimals(address token) external view returns (uint8 decimals);
}
