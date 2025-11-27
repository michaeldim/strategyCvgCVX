// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import {BaseStrategy, ERC20} from "@tokenized-strategy/BaseStrategy.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ICvgCvxStaking} from "./interfaces/ICvgCvxStaking.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title Staked cvgCVX Compounder
 * @notice This strategy stakes cvgCVX and auto-compounds cvgCVX rewards back into the position.
 */
contract StkCVGCVXStrategy is BaseStrategy {
    using SafeERC20 for ERC20;

    // --- Strategy state ---
    ICvgCvxStaking public constant STAKING =
        ICvgCvxStaking(0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119);

    // -----------------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------------

    constructor(
        address _asset,
        string memory _name
    ) BaseStrategy(_asset, _name) {
        asset.forceApprove(address(STAKING), type(uint256).max);
    }

    // -----------------------------------------------------------------------
    // View Functions
    // -----------------------------------------------------------------------

    /**
     * @notice Returns the maximum amount that can be deposited
     * @return The maximum deposit amount, 0 if deposits are paused
     */
    function availableDepositLimit(
        address
    ) public view override returns (uint256) {
        return STAKING.depositPaused() ? 0 : type(uint256).max;
    }

    // -----------------------------------------------------------------------
    // Core Strategy Implementation
    // -----------------------------------------------------------------------

    /**
     * @dev Deploys up to '_amount' of asset in the yield source (stakes cvgCVX)
     * @param _amount Amount of cvgCVX to stake
     */
    function _deployFunds(uint256 _amount) internal override {
        STAKING.deposit(
            _amount,
            ICvgCvxStaking.IN_TOKEN_TYPE.cvgCVX,
            0,
            0,
            false
        );
    }

    /**
     * @dev Attempts to free '_amount' of asset (unstake cvgCVX)
     * @param _amount Amount of cvgCVX to unstake
     */
    function _freeFunds(uint256 _amount) internal override {
        STAKING.withdraw(_amount, ICvgCvxStaking.OUT_TOKEN_TYPE.cvgCVX, 0);
    }

    /**
     * @dev Core harvest function. Claims cvgCVX rewards and immediately restakes them
     * @return _totalAssets Total assets under management after harvest
     */
    function _harvestAndReport()
        internal
        virtual
        override
        returns (uint256 _totalAssets)
    {
        STAKING.claimCvgCvxRewards(address(this), 0, false);

        uint256 idleBalance = asset.balanceOf(address(this));
        if (idleBalance > 0 && !TokenizedStrategy.isShutdown()) {
            _deployFunds(idleBalance);
        }

        uint256 idleAssets = asset.balanceOf(address(this));
        uint256 stakedAssets = STAKING.balanceOf(address(this));
        _totalAssets = idleAssets + stakedAssets;

        return _totalAssets;
    }

    /**
     * @dev Emergency withdrawal if strategy is shutdown
     * @param _amount Amount of asset to withdraw
     */
    function _emergencyWithdraw(uint256 _amount) internal override {
        _freeFunds(_amount);
    }
}
