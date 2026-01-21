// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import {Script, console} from "forge-std/Script.sol";
import {CVGCVXStrategyTrigger} from "../src/CVGCVXStrategyTrigger.sol";

interface ICommonReportTrigger {
    function setCustomStrategyTrigger(address strategy, address trigger) external;
}

interface IStrategy {
    function setKeeper(address keeper) external;
}

interface IRoleManager {
    function updateKeeper(address vault, address keeper) external;
}

/**
 * @title Deploy CVG-CVX Strategy Trigger
 * @notice Deploys the custom trigger and registers it with CommonReportTrigger
 *
 * @dev setCustomStrategyTrigger() can only be called by strategy management
 *      Keeper already has REPORTING_MANAGER role on vault
 */
contract DeployCVGCVXTrigger is Script {
    // Our deployed strategy
    address constant STRATEGY = 0x8ED5AB1BA2b2E434361858cBD3CA9f374e8b0359;

    // Vault for the strategy
    address constant VAULT = 0x0849b046292293f78dF3002F8461f8A7e2eC2b82;

    // Yearn V3 Keeper (for automated harvesting)
    address constant KEEPER = 0x52605BbF54845f520a3E94792d019f62407db2f8;

    // RoleManager (same one used in SetupVaultKeeper.s.sol)
    address constant ROLE_MANAGER = 0x4b0a8e6170151f3797EEEDC043aC3Dd632C2Adef;

    // CommonReportTrigger
    address constant COMMON_TRIGGER = 0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147;

    function run() external returns (address triggerAddress) {
        console.log("\n========================================");
        console.log("Deploying CVG-CVX Strategy Trigger");
        console.log("& Setting up Automated Harvesting");
        console.log("========================================");
        console.log("Strategy:", STRATEGY);
        console.log("Vault:", VAULT);
        console.log("Keeper:", KEEPER);
        console.log("RoleManager:", ROLE_MANAGER);
        console.log("CommonReportTrigger:", COMMON_TRIGGER);
        console.log("========================================\n");

        vm.startBroadcast();

        // TX 1: Deploy the custom trigger
        console.log("[TX 1] Deploying CVGCVXStrategyTrigger...");
        CVGCVXStrategyTrigger trigger = new CVGCVXStrategyTrigger();
        triggerAddress = address(trigger);
        console.log("   -> Trigger deployed at:", triggerAddress);
        console.log("");

        // TX 2: Register trigger with CommonReportTrigger
        console.log("[TX 2] Registering trigger with CommonReportTrigger...");
        ICommonReportTrigger(COMMON_TRIGGER).setCustomStrategyTrigger(STRATEGY, triggerAddress);
        console.log("   -> Trigger registered for strategy");
        console.log("");

        // TX 3: Set keeper on strategy
        console.log("[TX 3] Setting keeper on strategy...");
        IStrategy(STRATEGY).setKeeper(KEEPER);
        console.log("   -> Keeper set to:", KEEPER);
        console.log("   -> Note: Keeper already has REPORTING_MANAGER role on vault");
        console.log("");

        vm.stopBroadcast();

        console.log("========================================");
        console.log("DEPLOYMENT COMPLETE!");
        console.log("========================================");
        console.log("Trigger Address:", triggerAddress);
        console.log("Strategy:", STRATEGY);
        console.log("Vault:", VAULT);
        console.log("Keeper:", KEEPER);
        console.log("");
        console.log("Permissions Set:");
        console.log("  - Custom trigger registered");
        console.log("  - Strategy keeper updated to", KEEPER);
        console.log("  - Keeper already has REPORTING_MANAGER role on vault");
        console.log("");
        console.log("Automated harvesting is now enabled!");
        console.log("========================================");

        return triggerAddress;
    }
}
