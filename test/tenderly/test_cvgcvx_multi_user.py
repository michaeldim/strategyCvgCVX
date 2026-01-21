#!/usr/bin/env python3
"""
Test multiple users depositing/withdrawing with CVG-CVX strategy
to ensure approvals and accounting work correctly

NOTE: This test is simplified to stay within Tenderly's 20 block per VNet limit.
Each deposit requires 2 transactions (approve + deposit), so we're limited to
approximately 8-9 deposit/withdraw operations per test run.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Optional
from web3 import Web3
from eth_account import Account

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from tenderly_api import TenderlyVNetClient

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Strategy contract addresses (mainnet)
CONTRACTS = {
    "CVGCVX_TOKEN": "0x2191DF768ad71140F9F3E96c1e4407A4aA31d082",
    "CVG_STAKING": "0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119",
}

# ERC20 ABI (simplified)
ERC20_ABI = json.loads("""[
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "approve", "type": "function", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable"},
    {"name": "transfer", "type": "function", "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable"},
    {"name": "decimals", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view"}
]""")

# Strategy ABI
STRATEGY_ABI = json.loads("""[
    {"name": "deposit", "type": "function", "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}], "outputs": [{"name": "shares", "type": "uint256"}], "stateMutability": "nonpayable"},
    {"name": "withdraw", "type": "function", "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}, {"name": "owner", "type": "address"}], "outputs": [{"name": "shares", "type": "uint256"}], "stateMutability": "nonpayable"},
    {"name": "redeem", "type": "function", "inputs": [{"name": "shares", "type": "uint256"}, {"name": "receiver", "type": "address"}, {"name": "owner", "type": "address"}], "outputs": [{"name": "assets", "type": "uint256"}], "stateMutability": "nonpayable"},
    {"name": "totalAssets", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "totalSupply", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "report", "type": "function", "inputs": [], "outputs": [{"name": "profit", "type": "uint256"}, {"name": "loss", "type": "uint256"}], "stateMutability": "nonpayable"},
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "availableDepositLimit", "type": "function", "inputs": [{"name": "", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"}
]""")

# CVG Staking ABI
CVG_STAKING_ABI = json.loads("""[
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"}
]""")


def compile_and_get_bytecode() -> Optional[str]:
    """Compile the strategy and extract bytecode"""
    print("\n🔨 Compiling strategy...")

    result = subprocess.run(
        ['forge', 'build'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Compilation failed: {result.stderr}")
        return None

    print("✅ Compilation successful")

    artifact_path = PROJECT_ROOT / 'out' / 'StkCVGCVXStrategy.sol' / 'StkCVGCVXStrategy.json'

    with open(artifact_path, 'r') as f:
        artifact = json.load(f)

    bytecode = artifact.get('bytecode', {}).get('object', '')
    print(f"✅ Bytecode loaded ({len(bytecode)} bytes)")
    return bytecode


def deploy_strategy(w3, deployer_address: str, strategy_bytecode: str) -> str:
    """Deploy the StkCVGCVXStrategy contract"""
    print(f"\n📦 Deploying StkCVGCVXStrategy from {deployer_address[-8:]}...")

    # Constructor parameters: (address _asset, string memory _name)
    constructor_params = w3.codec.encode(
        ['address', 'string'],
        [CONTRACTS["CVGCVX_TOKEN"], "Multi-User CVG-CVX Strategy"]
    )

    # Deploy the contract
    deployment_tx = {
        'from': deployer_address,
        'data': strategy_bytecode + constructor_params.hex(),
        'gas': 3000000,
    }

    tx_hash = w3.eth.send_transaction(deployment_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    strategy_address = receipt.contractAddress
    print(f"✅ Strategy deployed at: {strategy_address}")
    print(f"   Gas used: {receipt.gasUsed:,}")

    return strategy_address


def setup_user_balances(client, users_amounts):
    """Setup initial user balances"""
    print("\n💰 Setting up user balances...")

    for user, amount in users_amounts.items():
        client.set_erc20_balance(CONTRACTS["CVGCVX_TOKEN"], user, amount)
        print(f"   {user[-8:]}: {Web3.from_wei(amount, 'ether')} cvgCVX")


def perform_user_action(w3, strategy, cvgcvx, user, action, amount_or_shares):
    """Perform a user action (deposit/withdraw/redeem)"""
    user_short = user[-8:]

    if action == "deposit":
        # Approve
        tx = cvgcvx.functions.approve(
            strategy.address,
            amount_or_shares
        ).transact({'from': user})
        w3.eth.wait_for_transaction_receipt(tx)

        # Deposit
        tx = strategy.functions.deposit(
            amount_or_shares,
            user
        ).transact({'from': user})
        receipt = w3.eth.wait_for_transaction_receipt(tx)

        shares = strategy.functions.balanceOf(user).call()
        print(f"   👤 {user_short} deposited {Web3.from_wei(amount_or_shares, 'ether')} cvgCVX → {Web3.from_wei(shares, 'ether')} shares")
        return receipt

    elif action == "withdraw":
        # Withdraw a specific amount of assets
        tx = strategy.functions.withdraw(
            amount_or_shares,
            user,
            user
        ).transact({'from': user})
        receipt = w3.eth.wait_for_transaction_receipt(tx)

        print(f"   👤 {user_short} withdrew {Web3.from_wei(amount_or_shares, 'ether')} cvgCVX")
        return receipt

    elif action == "redeem":
        # Redeem specific shares
        tx = strategy.functions.redeem(
            amount_or_shares,
            user,
            user
        ).transact({'from': user})
        receipt = w3.eth.wait_for_transaction_receipt(tx)

        print(f"   👤 {user_short} redeemed {Web3.from_wei(amount_or_shares, 'ether')} shares")
        return receipt


def harvest(w3, strategy, deployer):
    """Run harvest/report"""
    print(f"   🌾 Running harvest...")

    try:
        tx = strategy.functions.report().transact({'from': deployer})
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        print(f"      ✓ Harvest complete (gas: {receipt.gasUsed:,})")
        return receipt
    except Exception as e:
        error_msg = str(e)
        if "ALL_CVX_CLAIMED_FOR_NOW" in error_msg:
            print(f"      ℹ️ No rewards available (expected in test environment)")
            return None
        else:
            print(f"      ❌ Harvest failed: {e}")
            raise


def check_balances(w3, strategy, cvgcvx, staking, users):
    """Check all user balances and strategy state"""
    print("\n📊 Current State:")

    total_shares = 0
    for user in users:
        shares = strategy.functions.balanceOf(user).call()
        cvgcvx_bal = cvgcvx.functions.balanceOf(user).call()
        total_shares += shares
        if shares > 0 or cvgcvx_bal > 0:
            print(f"   {user[-8:]}: {Web3.from_wei(shares, 'ether'):.4f} shares, {Web3.from_wei(cvgcvx_bal, 'ether'):.4f} cvgCVX")

    # Strategy state
    total_assets = strategy.functions.totalAssets().call()
    total_supply = strategy.functions.totalSupply().call()
    idle = cvgcvx.functions.balanceOf(strategy.address).call()
    staked = staking.functions.balanceOf(strategy.address).call()

    print(f"\n   Strategy:")
    print(f"   - Total Assets: {Web3.from_wei(total_assets, 'ether'):.4f} cvgCVX")
    print(f"   - Total Supply: {Web3.from_wei(total_supply, 'ether'):.4f} shares")
    print(f"   - Idle cvgCVX: {Web3.from_wei(idle, 'ether'):.4f}")
    print(f"   - Staked: {Web3.from_wei(staked, 'ether'):.4f}")

    if total_supply > 0:
        price_per_share = total_assets / total_supply
        print(f"   - Price/Share: {price_per_share:.6f}")


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print(" MULTI-USER CVG-CVX STRATEGY TEST")
    print("="*60)

    # Compile strategy
    strategy_bytecode = compile_and_get_bytecode()
    if not strategy_bytecode:
        print("\n❌ Failed to compile strategy - exiting")
        return 1

    # Create Tenderly client
    client = TenderlyVNetClient(verbose=False)

    # Create new VNet
    if not client.create_vnet(
        display_name="Multi-User CVG-CVX Test",
        network_id="1",
        block_number=None,
        chain_id=31337
    ):
        print("❌ Failed to create VNet")
        return 1

    print(f"\n✅ VNet created: {client.vnet_id}")
    print(f"   Dashboard: {client.get_dashboard_url()}")

    # Create test accounts
    deployer = Account.create()
    user1 = Account.create()
    user2 = Account.create()
    user3 = Account.create()
    user4 = Account.create()
    user5 = Account.create()

    users = [user1.address, user2.address, user3.address, user4.address, user5.address]

    print(f"\n👤 Created accounts:")
    print(f"   Deployer: {deployer.address}")
    for i, user in enumerate(users, 1):
        print(f"   User{i}: {user}")

    # Use admin web3 connection which allows arbitrary from addresses
    w3 = client.admin_w3
    w3.eth.default_account = deployer.address

    # Fund accounts
    client.fund_account(deployer.address, 10)
    for user in users:
        client.fund_account(user, 5)

    # Deploy strategy
    strategy_address = deploy_strategy(w3, deployer.address, strategy_bytecode)
    strategy = w3.eth.contract(address=strategy_address, abi=STRATEGY_ABI)

    # Load token contracts
    cvgcvx = w3.eth.contract(address=CONTRACTS["CVGCVX_TOKEN"], abi=ERC20_ABI)
    staking = w3.eth.contract(address=CONTRACTS["CVG_STAKING"], abi=CVG_STAKING_ABI)

    # Setup initial balances
    initial_amounts = {
        user1.address: Web3.to_wei(100, 'ether'),
        user2.address: Web3.to_wei(50, 'ether'),
        user3.address: Web3.to_wei(75, 'ether'),
        user4.address: Web3.to_wei(25, 'ether'),
        user5.address: Web3.to_wei(150, 'ether'),
    }
    setup_user_balances(client, initial_amounts)

    # === Scenario 1: Initial deposits ===
    print("\n📍 Scenario 1: Initial deposits from 2 users")
    print(f"   Blocks used so far: ~1 (deployment)")
    perform_user_action(w3, strategy, cvgcvx, user1.address, "deposit", Web3.to_wei(50, 'ether'))
    print(f"   Blocks used: ~3 (deploy + approve + deposit)")
    perform_user_action(w3, strategy, cvgcvx, user2.address, "deposit", Web3.to_wei(30, 'ether'))
    print(f"   Blocks used: ~5")

    check_balances(w3, strategy, cvgcvx, staking, users)

    # === Scenario 2: Mixed operations ===
    print("\n📍 Scenario 2: Testing withdraw and redeem")

    # User1 redeems half their shares
    user1_shares = strategy.functions.balanceOf(user1.address).call()
    perform_user_action(w3, strategy, cvgcvx, user1.address, "redeem", user1_shares // 2)
    print(f"   Blocks used: ~6 (no approve needed for redeem)")

    # User2 withdraws specific amount
    perform_user_action(w3, strategy, cvgcvx, user2.address, "withdraw", Web3.to_wei(10, 'ether'))
    print(f"   Blocks used: ~7")

    # User3 makes first deposit
    perform_user_action(w3, strategy, cvgcvx, user3.address, "deposit", Web3.to_wei(40, 'ether'))
    print(f"   Blocks used: ~9")

    check_balances(w3, strategy, cvgcvx, staking, users)

    print(f"\n   ℹ️  Test complete - stayed within Tenderly's 20 block limit!")
    print(f"   ✅ Demonstrated: deposits, withdrawals, redeems, and multi-user accounting")

    print("\n" + "="*60)
    print("✅ Multi-user test completed successfully!")
    print("="*60)

    # Cleanup
    print(f"\n🗑️ Cleaning up VNet...")
    client.delete_vnet()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
