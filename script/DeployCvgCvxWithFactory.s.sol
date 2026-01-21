// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.18;

import "forge-std/Script.sol";
import {CVGCVXStrategyFactory} from "../src/CVGCVXStrategyFactory.sol";
import {StkCVGCVXStrategy} from "../src/StkCVGCVXStrategy.sol";
import {ITokenizedStrategy} from "@tokenized-strategy/interfaces/ITokenizedStrategy.sol";

contract DeployCvgCvxWithFactory is Script {
    // === ADDRESSES ===
    address constant CVGCVX_TOKEN = 0x2191DF768ad71140F9F3E96c1e4407A4aA31d082;
    address constant PENDING_MANAGEMENT = 0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3;
    address constant KEEPER = 0xa88e98bBD2Af6DDD642407cB5455f956f0C553F0;

    // For factory constructor
    address constant PERFORMANCE_FEE_RECIPIENT = 0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3; // Set to management (fee will be 0%)
    address constant EMERGENCY_ADMIN = 0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3; // Same as management

    string constant STRATEGY_NAME = "Staked cvgCVX Compounder";

    function run() external returns (address, address) {
        address deployer;

        // Check if using Ledger
        string memory privateKeyStr = vm.envOr("PRIVATE_KEY", string(""));
        bool usingLedger = bytes(privateKeyStr).length == 0;

        if (usingLedger) {
            deployer = msg.sender;
            require(deployer == PENDING_MANAGEMENT, "Deployer must be pending management");
            console.log("\n========================================");
            console.log("Deploying CVG-CVX Strategy with Factory");
            console.log("Using LEDGER");
            console.log("Deployer:", deployer);
            console.log("========================================\n");
            vm.startBroadcast();
        } else {
            uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
            deployer = vm.addr(deployerPrivateKey);
            require(deployer == PENDING_MANAGEMENT, "Deployer must be pending management");
            console.log("\n========================================");
            console.log("Deploying CVG-CVX Strategy with Factory");
            console.log("Using PRIVATE KEY");
            console.log("Deployer:", deployer);
            console.log("========================================\n");
            vm.startBroadcast(deployerPrivateKey);
        }

        // === TRANSACTION 1: Deploy Factory ===
        console.log("[TX 1] Deploying CVG-CVX Strategy Factory...");
        CVGCVXStrategyFactory factory = new CVGCVXStrategyFactory(
            PENDING_MANAGEMENT,        // management
            PERFORMANCE_FEE_RECIPIENT, // performance fee recipient
            KEEPER,                     // keeper
            EMERGENCY_ADMIN            // emergency admin
        );
        console.log("   -> Factory deployed at:", address(factory));

        // === TRANSACTION 2: Deploy Strategy via Factory ===
        console.log("\n[TX 2] Deploying strategy via factory...");
        address strategyAddress = factory.newStrategy(CVGCVX_TOKEN, STRATEGY_NAME);
        console.log("   -> Strategy deployed at:", strategyAddress);

        StkCVGCVXStrategy strategy = StkCVGCVXStrategy(strategyAddress);
        ITokenizedStrategy tokenizedStrategy = ITokenizedStrategy(strategyAddress);

        // === TRANSACTION 3: Accept Management ===
        console.log("\n[TX 3] Accepting management...");
        tokenizedStrategy.acceptManagement();
        console.log("   -> Management accepted");

        // === TRANSACTION 4: Set performance fee to 0% ===
        console.log("\n[TX 4] Setting performance fee to 0%...");
        tokenizedStrategy.setPerformanceFee(0);
        console.log("   -> Performance fee set to 0%");

        // Note: Keeper is already set by factory
        console.log("\n[INFO] Keeper already set by factory to:", KEEPER);

        vm.stopBroadcast();

        console.log("\n========================================");
        console.log("DEPLOYMENT COMPLETE!");
        console.log("========================================");
        console.log("Factory:", address(factory));
        console.log("Strategy:", strategyAddress);
        console.log("\nConfiguration:");
        console.log("  Asset (cvgCVX):", CVGCVX_TOKEN);
        console.log("  Management:", PENDING_MANAGEMENT);
        console.log("  Keeper:", KEEPER);
        console.log("  Performance Fee: 0%");
        console.log("\n========================================");
        console.log("Total transactions: 4");
        console.log("Estimated gas: ~2-3M");
        console.log("\n========================================");
        console.log("STRATEGY FEATURES:");
        console.log("========================================");
        console.log("- Stakes cvgCVX in CVG staking contract");
        console.log("- Rewards are cvgCVX (same as asset)");
        console.log("- Auto-compounds rewards by restaking");
        console.log("- NO auctions needed (rewards = asset!)");
        console.log("- NO swaps needed (1:1 deposit/withdraw)");
        console.log("- NO fees (avoids 0.25% conversion fee)");
        console.log("\n========================================");
        console.log("NEXT STEPS:");
        console.log("========================================");
        console.log("1. Deploy or use existing cvgCVX vault");
        console.log("\n2. Add strategy to vault:");
        console.log("   vault.add_strategy(", strategyAddress, ")");
        console.log("\n3. Set debt ratio for strategy in vault");
        console.log("\n4. (Optional) Set up CommonReportTrigger:");
        console.log("   - Deploy CVGCVXStrategyTrigger");
        console.log("   - Call setCustomStrategyTrigger() on CommonReportTrigger");
        console.log("\n5. Verify contracts on Etherscan");
        console.log("========================================");

        return (address(factory), strategyAddress);
    }
}
