// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import {ICvgCvxStaking} from "./interfaces/ICvgCvxStaking.sol";

/**
 * @title Custom Strategy Trigger Base
 * @author Yearn.finance
 */
abstract contract CustomStrategyTriggerBase {
    function reportTrigger(
        address _strategy
    ) external view virtual returns (bool, bytes memory);
}

interface IStrategy {
    function isShutdown() external view returns (bool);
    function totalAssets() external view returns (uint256);
    function lastReport() external view returns (uint256);
    function profitMaxUnlockTime() external view returns (uint256);
}

interface IBaseFee {
    function basefee_global() external view returns (uint256);
}

interface ICommonReportTrigger {
    function baseFeeProvider() external view returns (address);
    function acceptableBaseFee() external view returns (uint256);
}

/**
 * @title CVGCVXStrategyTrigger
 * @notice Custom report trigger for cvgCVX strategy
 * @dev Only triggers harvest when claimable rewards exist
 *      Respects strategy's profitMaxUnlockTime to prevent excessive reporting
 *      Uses CommonReportTrigger's base fee settings to prevent expensive harvests
 */
contract CVGCVXStrategyTrigger is CustomStrategyTriggerBase {
    // CVG staking contract to check claimable rewards
    ICvgCvxStaking public constant STAKING =
        ICvgCvxStaking(0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119);

    // Yearn's CommonReportTrigger for base fee checks
    ICommonReportTrigger public constant COMMON_TRIGGER =
        ICommonReportTrigger(0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147);

    /**
     * @notice Determines if strategy should report based on claimable rewards
     * @param _strategy Address of the cvgCVX strategy
     * @return . True if strategy should report
     * @return . Encoded call data or reason for not reporting
     */
    function reportTrigger(
        address _strategy
    ) external view override returns (bool, bytes memory) {
        IStrategy strategy = IStrategy(_strategy);

        // Don't report if strategy is shutdown
        if (strategy.isShutdown()) {
            return (false, bytes("Strategy is shutdown"));
        }

        // Don't report if no assets deployed
        if (strategy.totalAssets() == 0) {
            return (false, bytes("No assets deployed"));
        }

        // Ensure profit unlock time has passed since last report
        uint256 timeSinceLastReport = block.timestamp - strategy.lastReport();
        if (timeSinceLastReport <= strategy.profitMaxUnlockTime()) {
            return (false, bytes("Profit unlock time not reached"));
        }

        // Check base fee if provider is configured
        address baseFeeProvider = COMMON_TRIGGER.baseFeeProvider();
        if (baseFeeProvider != address(0)) {
            uint256 currentBaseFee = IBaseFee(baseFeeProvider).basefee_global();
            uint256 acceptableBaseFee = COMMON_TRIGGER.acceptableBaseFee();

            if (currentBaseFee > acceptableBaseFee) {
                return (false, bytes("Base fee too high"));
            }
        }

        // Check if there are claimable rewards
        (
            uint256 cvgAmount,
            ICvgCvxStaking.TokenAmount[] memory cvxRewards
        ) = STAKING.getAllClaimableAmounts(_strategy);

        // Check if cvgCVX rewards exist and are non-zero
        bool hasRewards = false;
        for (uint256 i = 0; i < cvxRewards.length; i++) {
            if (cvxRewards[i].amount > 0) {
                hasRewards = true;
                break;
            }
        }

        if (!hasRewards && cvgAmount == 0) {
            return (false, bytes("No rewards available"));
        }

        // All checks passed - rewards exist, time to report!
        return (true, abi.encodeWithSignature("report()"));
    }
}
