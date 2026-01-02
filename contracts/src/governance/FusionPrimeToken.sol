// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";

/**
 * @title FusionPrimeToken
 * @notice Governance token for Fusion Prime protocol
 * @dev ERC20 with voting capabilities (ERC20Votes) and permit (ERC20Permit)
 *
 * Token Distribution:
 * - 40% Community (liquidity mining, airdrops)
 * - 25% Team (4-year vesting, 1-year cliff)
 * - 20% Investors (3-year vesting)
 * - 10% Treasury (governance-controlled)
 * - 5% Advisors (2-year vesting)
 */
contract FusionPrimeToken is ERC20, ERC20Permit, ERC20Votes {
    // Total supply: 100 million tokens
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 1e18;

    // Distribution amounts
    uint256 public constant COMMUNITY_ALLOCATION = 40_000_000 * 1e18; // 40%
    uint256 public constant TEAM_ALLOCATION = 25_000_000 * 1e18; // 25%
    uint256 public constant INVESTOR_ALLOCATION = 20_000_000 * 1e18; // 20%
    uint256 public constant TREASURY_ALLOCATION = 10_000_000 * 1e18; // 10%
    uint256 public constant ADVISOR_ALLOCATION = 5_000_000 * 1e18; // 5%

    // Distribution recipients (set during deployment)
    address public immutable communityPool;
    address public immutable teamVesting;
    address public immutable investorVesting;
    address public immutable treasury;
    address public immutable advisorVesting;

    // Events
    event TokensDistributed(
        address indexed communityPool,
        address indexed treasury,
        address teamVesting,
        address investorVesting,
        address advisorVesting
    );

    /**
     * @notice Deploy the FP token and distribute to allocation addresses
     * @param _communityPool Address for community allocation (liquidity mining)
     * @param _teamVesting Address for team vesting contract
     * @param _investorVesting Address for investor vesting contract
     * @param _treasury Address for protocol treasury (governance-controlled)
     * @param _advisorVesting Address for advisor vesting contract
     */
    constructor(
        address _communityPool,
        address _teamVesting,
        address _investorVesting,
        address _treasury,
        address _advisorVesting
    ) ERC20("Fusion Prime", "FP") ERC20Permit("Fusion Prime") {
        require(_communityPool != address(0), "Invalid community pool");
        require(_teamVesting != address(0), "Invalid team vesting");
        require(_investorVesting != address(0), "Invalid investor vesting");
        require(_treasury != address(0), "Invalid treasury");
        require(_advisorVesting != address(0), "Invalid advisor vesting");

        communityPool = _communityPool;
        teamVesting = _teamVesting;
        investorVesting = _investorVesting;
        treasury = _treasury;
        advisorVesting = _advisorVesting;

        // Mint and distribute tokens
        _mint(_communityPool, COMMUNITY_ALLOCATION);
        _mint(_teamVesting, TEAM_ALLOCATION);
        _mint(_investorVesting, INVESTOR_ALLOCATION);
        _mint(_treasury, TREASURY_ALLOCATION);
        _mint(_advisorVesting, ADVISOR_ALLOCATION);

        emit TokensDistributed(
            _communityPool,
            _treasury,
            _teamVesting,
            _investorVesting,
            _advisorVesting
        );
    }

    // ========== OVERRIDES ==========

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {
        super._update(from, to, value);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}
