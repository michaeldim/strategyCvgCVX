// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import "forge-std/Script.sol";
import {CVGCVXStrategyTrigger} from "../src/CVGCVXStrategyTrigger.sol";

/**
 * @title Deploy CvgCvxStrategyTrigger
 * @notice Deploys the custom report trigger for cvgCVX strategy
 * @dev Usage:
 *      forge script script/DeployCvgCvxStrategyTrigger.s.sol:DeployCvgCvxStrategyTrigger --broadcast --verify
 */
contract DeployCvgCvxStrategyTrigger is Script {
    function run() external {
        vm.startBroadcast();

        // Deploy the trigger contract
        CVGCVXStrategyTrigger trigger = new CVGCVXStrategyTrigger();

        console.log("========================================");
        console.log("CvgCvxStrategyTrigger deployed at:", address(trigger));
        console.log("========================================");
        console.log("");
        console.log("Next step:");
        console.log("Call CommonReportTrigger(0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147)");
        console.log("  .setCustomStrategyTrigger(STRATEGY_ADDRESS,", address(trigger), ")");
        console.log("");
        console.log("NOTE: This trigger can be shared by ALL cvgCVX strategies!");
        console.log("========================================");

        vm.stopBroadcast();
    }
}
