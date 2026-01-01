// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IPriceOracle
 * @notice Interface for price oracles used by CrossChainVault
 */
interface IPriceOracle {
    /**
     * @notice Get latest price for native token in USD
     * @return price Price in USD with 8 decimals (e.g., 300000000000 = $3000.00)
     */
    function getNativePrice() external view returns (uint256);

    /**
     * @notice Convert native token amount to USD value
     * @param amount Token amount with 18 decimals (e.g., 1 ETH = 1e18)
     * @return usdValue USD value with 18 decimals (e.g., $3000 = 3000e18)
     */
    function convertToUSD(uint256 amount) external view returns (uint256 usdValue);

    /**
     * @notice Convert USD value to native token amount
     * @param usdValue USD value with 18 decimals (e.g., $3000 = 3000e18)
     * @return amount Token amount with 18 decimals (e.g., 1 ETH = 1e18)
     */
    function convertFromUSD(uint256 usdValue) external view returns (uint256 amount);
}
