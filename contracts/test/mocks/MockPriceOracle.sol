// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {
    IMultiTokenPriceOracle
} from "interfaces/IMultiTokenPriceOracle.sol";

/**
 * @title MockPriceOracle
 * @notice Configurable mock oracle for local testing
 * @dev Allows tests to set and manipulate prices for ETH and ERC20 tokens
 */
contract MockPriceOracle is IMultiTokenPriceOracle {
    // Price storage (8 decimals like Chainlink)
    uint256 public nativePrice; // ETH/USD price
    mapping(address => uint256) public tokenPrices; // token => price (8 decimals)
    mapping(address => uint8) public tokenDecimals; // token => decimals
    mapping(address => bool) public supportedTokens;

    // Owner for admin functions
    address public owner;

    // Constants
    uint8 public constant PRICE_DECIMALS = 8;

    // Events
    event NativePriceUpdated(uint256 oldPrice, uint256 newPrice);
    event TokenPriceUpdated(
        address indexed token,
        uint256 oldPrice,
        uint256 newPrice
    );
    event TokenAdded(address indexed token, uint256 price, uint8 decimals);

    constructor() {
        owner = msg.sender;
        // Default: ETH = $2000
        nativePrice = 2000 * 10 ** PRICE_DECIMALS;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // ============================================
    // Price Configuration (for tests)
    // ============================================

    /**
     * @notice Set native token (ETH) price
     * @param price Price in USD with 8 decimals (e.g., 2000e8 = $2000)
     */
    function setNativePrice(uint256 price) external onlyOwner {
        uint256 oldPrice = nativePrice;
        nativePrice = price;
        emit NativePriceUpdated(oldPrice, price);
    }

    /**
     * @notice Add a supported token with price
     * @param token Token address
     * @param price Price in USD with 8 decimals
     * @param decimals Token decimals (e.g., 6 for USDC)
     */
    function addToken(
        address token,
        uint256 price,
        uint8 decimals
    ) external onlyOwner {
        supportedTokens[token] = true;
        tokenPrices[token] = price;
        tokenDecimals[token] = decimals;
        emit TokenAdded(token, price, decimals);
    }

    /**
     * @notice Update token price (for liquidation tests)
     * @param token Token address
     * @param price New price in USD with 8 decimals
     */
    function setTokenPrice(address token, uint256 price) external onlyOwner {
        require(supportedTokens[token], "Token not supported");
        uint256 oldPrice = tokenPrices[token];
        tokenPrices[token] = price;
        emit TokenPriceUpdated(token, oldPrice, price);
    }

    // ============================================
    // IPriceOracle Implementation (Native Token)
    // ============================================

    function getNativePrice() external view override returns (uint256) {
        return nativePrice;
    }

    function convertToUSD(
        uint256 amount
    ) external view override returns (uint256 usdValue) {
        // amount is in wei (18 decimals), price has 8 decimals
        // result should have 18 decimals
        usdValue = (amount * nativePrice) / (10 ** PRICE_DECIMALS);
    }

    function convertFromUSD(
        uint256 usdValue
    ) external view override returns (uint256 amount) {
        // usdValue has 18 decimals, price has 8 decimals
        // result should have 18 decimals
        amount = (usdValue * (10 ** PRICE_DECIMALS)) / nativePrice;
    }

    // ============================================
    // IMultiTokenPriceOracle Implementation
    // ============================================

    function getTokenPrice(
        address token
    ) external view override returns (uint256 price) {
        require(supportedTokens[token], "Token not supported");
        return tokenPrices[token];
    }

    function convertTokenToUSD(
        address token,
        uint256 amount
    ) external view override returns (uint256 usdValue) {
        require(supportedTokens[token], "Token not supported");
        uint256 price = tokenPrices[token];
        uint8 decimals = tokenDecimals[token];

        // Normalize to 18 decimals, then apply price
        if (decimals < 18) {
            usdValue =
                ((amount * price) / (10 ** PRICE_DECIMALS)) *
                (10 ** (18 - decimals));
        } else if (decimals > 18) {
            usdValue =
                (amount * price) /
                (10 ** PRICE_DECIMALS) /
                (10 ** (decimals - 18));
        } else {
            usdValue = (amount * price) / (10 ** PRICE_DECIMALS);
        }
    }

    function convertUSDToToken(
        address token,
        uint256 usdValue
    ) external view override returns (uint256 amount) {
        require(supportedTokens[token], "Token not supported");
        uint256 price = tokenPrices[token];
        uint8 decimals = tokenDecimals[token];

        // Convert from 18 decimal USD to token decimals
        if (decimals < 18) {
            amount =
                (usdValue * (10 ** PRICE_DECIMALS)) /
                price /
                (10 ** (18 - decimals));
        } else if (decimals > 18) {
            amount =
                (usdValue * (10 ** PRICE_DECIMALS) * (10 ** (decimals - 18))) /
                price;
        } else {
            amount = (usdValue * (10 ** PRICE_DECIMALS)) / price;
        }
    }

    function isTokenSupported(
        address token
    ) external view override returns (bool supported) {
        return supportedTokens[token];
    }

    function getTokenDecimals(
        address token
    ) external view override returns (uint8) {
        return tokenDecimals[token];
    }
}
