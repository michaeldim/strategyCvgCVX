// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.18;

import "forge-std/Script.sol";
import {StkCVGCVXStrategy} from "../src/StkCVGCVXStrategy.sol";
import {ITokenizedStrategy} from "@tokenized-strategy/interfaces/ITokenizedStrategy.sol";

interface IStrategyFactory {
    function newStrategy(
        address _asset,
        string memory _name
    ) external returns (address);
}

contract DeployCvgCvxStrategy is Script {
    // === ADDRESSES ===
    address constant CVGCVX_TOKEN = 0x2191DF768ad71140F9F3E96c1e4407A4aA31d082;
    address constant STAKING_CONTRACT = 0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119;

    // Factory and Management
    address constant STRATEGY_FACTORY = 0x34f9C1952EcAe0C6c73116eC88E4871d0595eF97;
    address constant PENDING_MANAGEMENT = 0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3;

    // Governance/Management addresses
    address constant KEEPER = 0xa88e98bBD2Af6DDD642407cB5455f956f0C553F0; // Strategy keeper

    // Deployment parameters
    string constant STRATEGY_NAME = "CVG cvgCVX Staking Compounder";

    function run() external {
        address deployer;

        // Check if using Ledger by checking if PRIVATE_KEY is set
        string memory privateKeyStr = vm.envOr("PRIVATE_KEY", string(""));
        bool usingLedger = bytes(privateKeyStr).length == 0;

        if (usingLedger) {
            // When using Ledger, msg.sender will be the --sender address
            deployer = msg.sender;
            require(deployer == PENDING_MANAGEMENT, "Deployer must be pending management address");

            console.log("========================================");
            console.log("Deploying CVG cvgCVX Strategy via Factory");
            console.log("Using LEDGER");
            console.log("Deployer (Management):", deployer);
            console.log("========================================\n");

            vm.startBroadcast();
        } else {
            // Using private key
            uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
            deployer = vm.addr(deployerPrivateKey);

            require(deployer == PENDING_MANAGEMENT, "Deployer must be pending management address");

            console.log("========================================");
            console.log("Deploying CVG cvgCVX Strategy via Factory");
            console.log("Using PRIVATE KEY");
            console.log("Deployer (Management):", deployer);
            console.log("========================================\n");

            vm.startBroadcast(deployerPrivateKey);
        }

        // === 1. Deploy Strategy via Factory ===
        console.log("1. Deploying strategy via factory...");
        address strategyAddress = IStrategyFactory(STRATEGY_FACTORY).newStrategy(
            CVGCVX_TOKEN,
            STRATEGY_NAME
        );
        console.log("   -> Strategy deployed at:", strategyAddress);

        StkCVGCVXStrategy strategy = StkCVGCVXStrategy(strategyAddress);
        ITokenizedStrategy tokenizedStrategy = ITokenizedStrategy(strategyAddress);

        // === 2. Accept Management ===
        console.log("\n2. Accepting management...");
        tokenizedStrategy.acceptManagement();
        console.log("   -> Management accepted");

        // === 3. Set performance fee to 0 ===
        console.log("\n3. Setting performance fee to 0...");
        tokenizedStrategy.setPerformanceFee(0);
        console.log("   -> Performance fee set to 0");

        // === 4. Set keeper ===
        console.log("\n4. Setting keeper...");
        tokenizedStrategy.setKeeper(KEEPER);
        console.log("   -> Keeper set to:", KEEPER);

        vm.stopBroadcast();

        // === Summary ===
        console.log("\n========================================");
        console.log("Deployment Complete!");
        console.log("========================================");
        console.log("Strategy:", address(strategy));
        console.log("Asset (cvgCVX):", CVGCVX_TOKEN);
        console.log("Staking Contract:", STAKING_CONTRACT);
        console.log("Keeper:", KEEPER);
        console.log("\nStrategy Features:");
        console.log("- Stakes cvgCVX in CVG staking contract");
        console.log("- Rewards are cvgCVX (same as asset)");
        console.log("- Auto-compounds rewards by restaking");
        console.log("- NO auctions needed (rewards = asset!)");
        console.log("- NO swaps needed (1:1 deposit/withdraw)");
        console.log("- NO fees (0.25% avoided with direct cvgCVX)");
        console.log("\nNext steps:");
        console.log("1. Create or use existing cvgCVX vault");
        console.log("2. Add strategy to vault: vault.add_strategy(", address(strategy), ")");
        console.log("3. Set debt ratio for strategy in vault");
        console.log("4. Verify contract on Etherscan");
        console.log("========================================");
    }
}
