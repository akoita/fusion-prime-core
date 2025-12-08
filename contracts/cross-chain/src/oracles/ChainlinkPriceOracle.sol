// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/AggregatorV3Interface.sol";

/**
 * @title ChainlinkPriceOracle
 * @notice Provides USD price feeds for cross-chain asset valuation
 * @dev Uses Chainlink price feeds to convert native token amounts to USD values
 */
contract ChainlinkPriceOracle {
    // Price feed for the native token (ETH on Sepolia, MATIC on Amoy)
    AggregatorV3Interface public nativePriceFeed;

    // Owner for price feed updates
    address public owner;

    // Decimals: Chainlink returns 8 decimals for USD prices
    uint8 public constant PRICE_DECIMALS = 8;

    // Token decimals (ETH and MATIC both use 18 decimals)
    uint8 public constant TOKEN_DECIMALS = 18;

    // Max price staleness (1 hour)
    uint256 public constant MAX_PRICE_AGE = 1 hours;

    // Events
    event PriceFeedUpdated(address indexed oldFeed, address indexed newFeed);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // Errors
    error Unauthorized();
    error StalePriceData();
    error InvalidPrice();
    error InvalidPriceFeed();
    error StaleRound();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    /**
     * @notice Constructor sets the native token price feed
     * @param _nativePriceFeed Address of Chainlink price feed for native token
     */
    constructor(address _nativePriceFeed) {
        if (_nativePriceFeed == address(0)) revert InvalidPriceFeed();
        nativePriceFeed = AggregatorV3Interface(_nativePriceFeed);
        owner = msg.sender;
    }

    /**
     * @notice Get latest price for native token in USD
     * @return price Price in USD with 8 decimals (e.g., 300000000000 = $3000.00)
     */
    function getNativePrice() public view returns (uint256) {
        (
            uint80 roundId,
            int256 price,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = nativePriceFeed.latestRoundData();

        // Validate data freshness (within 1 hour)
        if (updatedAt < block.timestamp - MAX_PRICE_AGE) revert StalePriceData();

        // Validate price is positive
        if (price <= 0) revert InvalidPrice();

        // Validate round data
        if (answeredInRound < roundId) revert StaleRound();

        return uint256(price);
    }

    /**
     * @notice Convert native token amount to USD value
     * @param amount Token amount with 18 decimals (e.g., 1 ETH = 1e18)
     * @return usdValue USD value with 18 decimals (e.g., $3000 = 3000e18)
     */
    function convertToUSD(uint256 amount) public view returns (uint256 usdValue) {
        uint256 price = getNativePrice(); // 8 decimals

        // Convert: (amount * price) / 10^8
        // Input: amount (18 decimals), price (8 decimals)
        // Output: USD value (18 decimals)
        usdValue = (amount * price) / (10 ** PRICE_DECIMALS);

        return usdValue;
    }

    /**
     * @notice Convert USD value to native token amount
     * @param usdValue USD value with 18 decimals (e.g., $3000 = 3000e18)
     * @return amount Token amount with 18 decimals (e.g., 1 ETH = 1e18)
     */
    function convertFromUSD(uint256 usdValue) public view returns (uint256 amount) {
        uint256 price = getNativePrice(); // 8 decimals

        // Convert: (usdValue * 10^8) / price
        // Input: usdValue (18 decimals), price (8 decimals)
        // Output: amount (18 decimals)
        amount = (usdValue * (10 ** PRICE_DECIMALS)) / price;

        return amount;
    }

    /**
     * @notice Get price feed metadata
     * @return decimals Price feed decimals (should be 8)
     * @return description Price feed description
     */
    function getPriceFeedMetadata() external view returns (uint8 decimals, string memory description) {
        decimals = nativePriceFeed.decimals();
        description = nativePriceFeed.description();
    }

    /**
     * @notice Update native token price feed (only owner)
     * @param _newPriceFeed New price feed address
     */
    function setPriceFeed(address _newPriceFeed) external onlyOwner {
        if (_newPriceFeed == address(0)) revert InvalidPriceFeed();

        address oldFeed = address(nativePriceFeed);
        nativePriceFeed = AggregatorV3Interface(_newPriceFeed);

        emit PriceFeedUpdated(oldFeed, _newPriceFeed);
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
