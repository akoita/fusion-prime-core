// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "interfaces/AggregatorV3Interface.sol";
import "interfaces/IMultiTokenPriceOracle.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";

/**
 * @title MultiTokenPriceOracle
 * @notice Provides USD price feeds for multiple tokens using Chainlink
 * @dev Supports native token and multiple ERC20 tokens (USDC, DAI, WETH, WBTC)
 */
contract MultiTokenPriceOracle is IMultiTokenPriceOracle {
    // Price feeds
    AggregatorV3Interface public nativePriceFeed;
    mapping(address => AggregatorV3Interface) public tokenPriceFeeds;
    mapping(address => uint8) public tokenDecimals;

    // Supported tokens
    mapping(address => bool) public supportedTokens;
    address[] public allTokens;

    // Owner
    address public owner;

    // Constants
    uint8 public constant PRICE_DECIMALS = 8;
    uint256 public constant MAX_PRICE_AGE = 1 hours;

    // Events
    event TokenPriceFeedAdded(address indexed token, address indexed priceFeed, uint8 decimals);
    event TokenPriceFeedRemoved(address indexed token);
    event NativePriceFeedUpdated(address indexed oldFeed, address indexed newFeed);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // Errors
    error Unauthorized();
    error StalePriceData();
    error InvalidPrice();
    error InvalidPriceFeed();
    error StaleRound();
    error TokenNotSupported();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    /**
     * @notice Constructor sets native token price feed
     * @param _nativePriceFeed Chainlink price feed for native token (ETH/USD or MATIC/USD)
     */
    constructor(address _nativePriceFeed) {
        if (_nativePriceFeed == address(0)) revert InvalidPriceFeed();
        nativePriceFeed = AggregatorV3Interface(_nativePriceFeed);
        owner = msg.sender;
    }

    /**
     * @notice Add a token price feed
     * @param token Token address
     * @param priceFeed Chainlink price feed address
     * @param decimals Token decimals (fetch from token if 0)
     */
    function addTokenPriceFeed(
        address token,
        address priceFeed,
        uint8 decimals
    ) external onlyOwner {
        if (token == address(0) || priceFeed == address(0)) revert InvalidPriceFeed();

        tokenPriceFeeds[token] = AggregatorV3Interface(priceFeed);
        supportedTokens[token] = true;

        // Get decimals from token if not provided
        if (decimals == 0) {
            try IERC20Metadata(token).decimals() returns (uint8 d) {
                decimals = d;
            } catch {
                decimals = 18; // Default to 18
            }
        }
        tokenDecimals[token] = decimals;

        // Add to list if not already present
        bool found = false;
        for (uint256 i = 0; i < allTokens.length; i++) {
            if (allTokens[i] == token) {
                found = true;
                break;
            }
        }
        if (!found) {
            allTokens.push(token);
        }

        emit TokenPriceFeedAdded(token, priceFeed, decimals);
    }

    /**
     * @notice Remove a token price feed
     * @param token Token address
     */
    function removeTokenPriceFeed(address token) external onlyOwner {
        supportedTokens[token] = false;
        delete tokenPriceFeeds[token];
        emit TokenPriceFeedRemoved(token);
    }

    /**
     * @notice Update native token price feed
     * @param newPriceFeed New price feed address
     */
    function setNativePriceFeed(address newPriceFeed) external onlyOwner {
        if (newPriceFeed == address(0)) revert InvalidPriceFeed();
        address oldFeed = address(nativePriceFeed);
        nativePriceFeed = AggregatorV3Interface(newPriceFeed);
        emit NativePriceFeedUpdated(oldFeed, newPriceFeed);
    }

    // ============================================
    // IPriceOracle Implementation (Native Token)
    // ============================================

    /**
     * @notice Get native token price in USD
     * @return price Price with 8 decimals
     */
    function getNativePrice() public view returns (uint256) {
        return _getValidPrice(nativePriceFeed);
    }

    /**
     * @notice Convert native token amount to USD
     * @param amount Amount in wei (18 decimals)
     * @return usdValue USD value with 18 decimals
     */
    function convertToUSD(uint256 amount) public view returns (uint256 usdValue) {
        uint256 price = getNativePrice();
        usdValue = (amount * price) / (10 ** PRICE_DECIMALS);
    }

    /**
     * @notice Convert USD to native token amount
     * @param usdValue USD value with 18 decimals
     * @return amount Amount in wei (18 decimals)
     */
    function convertFromUSD(uint256 usdValue) public view returns (uint256 amount) {
        uint256 price = getNativePrice();
        amount = (usdValue * (10 ** PRICE_DECIMALS)) / price;
    }

    // ============================================
    // IMultiTokenPriceOracle Implementation
    // ============================================

    /**
     * @notice Get token price in USD
     * @param token Token address
     * @return price Price with 8 decimals
     */
    function getTokenPrice(address token) public view returns (uint256 price) {
        if (!supportedTokens[token]) revert TokenNotSupported();
        AggregatorV3Interface feed = tokenPriceFeeds[token];
        return _getValidPrice(feed);
    }

    /**
     * @notice Convert token amount to USD
     * @param token Token address
     * @param amount Token amount (with token's decimals)
     * @return usdValue USD value with 18 decimals
     */
    function convertTokenToUSD(address token, uint256 amount) public view returns (uint256 usdValue) {
        if (!supportedTokens[token]) revert TokenNotSupported();

        uint256 price = getTokenPrice(token);
        uint8 decimals = tokenDecimals[token];

        // Normalize to 18 decimals, then apply price
        // Reorder operations to avoid overflow
        if (decimals < 18) {
            // First divide by price decimals, then multiply by normalization factor
            usdValue = (amount * price / (10 ** PRICE_DECIMALS)) * (10 ** (18 - decimals));
        } else if (decimals > 18) {
            usdValue = (amount * price) / (10 ** PRICE_DECIMALS) / (10 ** (decimals - 18));
        } else {
            usdValue = (amount * price) / (10 ** PRICE_DECIMALS);
        }
    }

    /**
     * @notice Convert USD to token amount
     * @param token Token address
     * @param usdValue USD value with 18 decimals
     * @return amount Token amount (with token's decimals)
     */
    function convertUSDToToken(address token, uint256 usdValue) public view returns (uint256 amount) {
        if (!supportedTokens[token]) revert TokenNotSupported();

        uint256 price = getTokenPrice(token);
        uint8 decimals = tokenDecimals[token];

        // Convert from 18 decimal USD to token decimals
        if (decimals < 18) {
            amount = (usdValue * (10 ** PRICE_DECIMALS)) / price / (10 ** (18 - decimals));
        } else if (decimals > 18) {
            amount = (usdValue * (10 ** PRICE_DECIMALS) * (10 ** (decimals - 18))) / price;
        } else {
            amount = (usdValue * (10 ** PRICE_DECIMALS)) / price;
        }
    }

    /**
     * @notice Check if token is supported
     * @param token Token address
     * @return supported True if supported
     */
    function isTokenSupported(address token) external view returns (bool supported) {
        return supportedTokens[token];
    }

    /**
     * @notice Get token decimals
     * @param token Token address
     * @return decimals Token decimals
     */
    function getTokenDecimals(address token) external view returns (uint8) {
        return tokenDecimals[token];
    }

    // ============================================
    // Internal Functions
    // ============================================

    /**
     * @notice Get validated price from Chainlink feed
     * @param feed Chainlink aggregator
     * @return price Valid price
     */
    function _getValidPrice(AggregatorV3Interface feed) internal view returns (uint256) {
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = feed.latestRoundData();

        if (updatedAt < block.timestamp - MAX_PRICE_AGE) revert StalePriceData();
        if (price <= 0) revert InvalidPrice();
        if (answeredInRound < roundId) revert StaleRound();

        return uint256(price);
    }

    // ============================================
    // View Functions
    // ============================================

    /**
     * @notice Get all supported tokens
     * @return tokens Array of token addresses
     */
    function getAllTokens() external view returns (address[] memory) {
        return allTokens;
    }

    /**
     * @notice Get price feed info for a token
     * @param token Token address
     * @return priceFeed Price feed address
     * @return decimals Token decimals
     * @return supported Is token supported
     */
    function getTokenInfo(address token)
        external
        view
        returns (
            address priceFeed,
            uint8 decimals,
            bool supported
        )
    {
        priceFeed = address(tokenPriceFeeds[token]);
        decimals = tokenDecimals[token];
        supported = supportedTokens[token];
    }

    /**
     * @notice Transfer ownership
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidPriceFeed();
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}
