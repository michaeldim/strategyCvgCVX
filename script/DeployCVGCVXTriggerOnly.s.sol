// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import {Script, console} from "forge-std/Script.sol";
import {CVGCVXStrategyTrigger} from "../src/CVGCVXStrategyTrigger.sol";

interface IStrategy {
    function setKeeper(address keeper) external;
}

/**
 * @title Deploy CVG-CVX Strategy Trigger (Part 1)
 * @notice Deploys the custom trigger and sets keeper on strategy
 *
 * @dev Governance must register the trigger separately via:
 *      CommonReportTrigger(0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147).setCustomTrigger(STRATEGY, trigger)
 */
contract DeployCVGCVXTriggerOnly is Script {
    // Our deployed strategy
    address constant STRATEGY = 0x8ED5AB1BA2b2E434361858cBD3CA9f374e8b0359;

    // Yearn V3 Keeper (for automated harvesting)
    address constant KEEPER = 0x52605BbF54845f520a3E94792d019f62407db2f8;

    // CommonReportTrigger (for governance to use)
    address constant COMMON_TRIGGER = 0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147;

    function run() external returns (address triggerAddress) {
        console.log("\n========================================");
        console.log("Deploying CVG-CVX Strategy Trigger");
        console.log("========================================");
        console.log("Strategy:", STRATEGY);
        console.log("Keeper:", KEEPER);
        console.log("CommonReportTrigger:", COMMON_TRIGGER);
        console.log("========================================\n");

        vm.startBroadcast();

        // TX 1: Deploy the custom trigger
        console.log("[TX 1] Deploying CVGCVXStrategyTrigger...");
        CVGCVXStrategyTrigger trigger = new CVGCVXStrategyTrigger();
        triggerAddress = address(trigger);
        console.log("   -> Trigger deployed at:", triggerAddress);
        console.log("");

        // TX 2: Set keeper on strategy
        console.log("[TX 2] Setting keeper on strategy...");
        IStrategy(STRATEGY).setKeeper(KEEPER);
        console.log("   -> Keeper set to:", KEEPER);
        console.log("");

        vm.stopBroadcast();

        console.log("========================================");
        console.log("DEPLOYMENT COMPLETE!");
        console.log("========================================");
        console.log("Trigger Address:", triggerAddress);
        console.log("Strategy:", STRATEGY);
        console.log("Keeper:", KEEPER);
        console.log("");
        console.log("NEXT STEPS:");
        console.log("  1. Submit governance proposal to register trigger:");
        console.log("     Call: CommonReportTrigger.setCustomTrigger(");
        console.log("       strategy:", STRATEGY);
        console.log("       trigger:", triggerAddress);
        console.log("     )");
        console.log("");
        console.log("  2. Or contact Yearn governance to register at:");
        console.log("     https://gov.yearn.fi");
        console.log("========================================");

        return triggerAddress;
    }
}
