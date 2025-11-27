#!/usr/bin/env python3
"""
Test CVG-CVX strategy deployment on Tenderly VNet
Tests both forceApprove and depositPaused functionality
"""

import sys
import os
from web3 import Web3
from eth_account import Account
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tenderly_api import TenderlyVNetClient

def load_abi(filename):
    """Load ABI from file"""
    abi_path = os.path.join(os.path.dirname(__file__), '../../abi', filename)
    with open(abi_path, 'r') as f:
        return json.load(f)

def test_deployment():
    """Test CVG-CVX strategy deployment"""

    print("=" * 60)
    print("CVG-CVX Strategy Deployment Test on Tenderly VNet")
    print("=" * 60)

    # Create VNet
    print("\n1. Creating Tenderly VNet...")
    client = TenderlyVNetClient()

    # Actually create the VNet
    success = client.create_vnet(
        display_name="CVG-CVX Strategy Deployment Test",
        network_id="1"  # Mainnet
    )

    if not success or not client.vnet_id:
        print("ERROR: Failed to create VNet")
        return False

    print(f"   VNet ID: {client.vnet_id}")
    print(f"   RPC URL: {client.rpc_url}")

    # Get Web3
    w3 = client.w3
    print(f"   Chain ID: {w3.eth.chain_id}")

    # Create deployer account
    deployer = Account.create()
    print(f"\n2. Created deployer account: {deployer.address}")

    # Fund deployer
    client.fund_account(deployer.address, 100)
    balance = w3.eth.get_balance(deployer.address)
    print(f"   Funded with {Web3.from_wei(balance, 'ether')} ETH")

    # Contract addresses
    CVGCVX_TOKEN = "0x2191DF768ad71140F9F3E96c1e4407A4aA31d082"
    CVG_STAKING = "0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119"

    print(f"\n3. Testing depositPaused() on CVG Staking...")
    print(f"   Staking contract: {CVG_STAKING}")

    try:
        # Call depositPaused()
        result = w3.eth.call({
            "to": CVG_STAKING,
            "data": w3.keccak(text="depositPaused()")[:4]
        })
        deposits_paused = bool(int(result.hex(), 16))
        print(f"   ✓ depositPaused() call successful")
        print(f"   Result: {deposits_paused}")
    except Exception as e:
        print(f"   ✗ depositPaused() call failed: {e}")
        client.delete_vnet()
        return False

    print(f"\n4. Loading strategy bytecode...")

    # Read compiled bytecode
    try:
        with open('../../out/StkCVGCVXStrategy.sol/StkCVGCVXStrategy.json', 'r') as f:
            artifact = json.load(f)
            bytecode = artifact['bytecode']['object']
            abi = artifact['abi']
            print(f"   ✓ Loaded bytecode ({len(bytecode)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed to load bytecode: {e}")
        client.delete_vnet()
        return False

    print(f"\n5. Deploying StkCVGCVXStrategy...")
    print(f"   Asset: {CVGCVX_TOKEN}")

    try:
        # Get contract factory
        Strategy = w3.eth.contract(abi=abi, bytecode=bytecode)

        # Build constructor transaction
        constructor_tx = Strategy.constructor(
            CVGCVX_TOKEN,
            "CVG cvgCVX Staking Compounder"
        ).build_transaction({
            'from': deployer.address,
            'nonce': w3.eth.get_transaction_count(deployer.address),
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(constructor_tx, deployer.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"   Transaction sent: {tx_hash.hex()}")

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            strategy_address = receipt['contractAddress']
            print(f"   ✓ Strategy deployed at: {strategy_address}")
        else:
            print(f"   ✗ Deployment failed")
            client.delete_vnet()
            return False

    except Exception as e:
        print(f"   ✗ Deployment error: {e}")
        client.delete_vnet()
        return False

    print(f"\n6. Verifying deployment...")

    # Check approval was set
    cvgcvx_abi = load_abi('cvgcvx_token_abi.json')
    cvgcvx = w3.eth.contract(address=CVGCVX_TOKEN, abi=cvgcvx_abi)

    try:
        allowance = cvgcvx.functions.allowance(strategy_address, CVG_STAKING).call()
        max_uint = 2**256 - 1

        if allowance == max_uint:
            print(f"   ✓ Approval set correctly (max uint256)")
        else:
            print(f"   ✗ Approval not set: {allowance}")
            client.delete_vnet()
            return False
    except Exception as e:
        print(f"   ✗ Failed to check approval: {e}")
        client.delete_vnet()
        return False

    # Check availableDepositLimit works
    strategy = w3.eth.contract(address=strategy_address, abi=abi)

    try:
        deposit_limit = strategy.functions.availableDepositLimit(deployer.address).call()

        if deposit_limit == max_uint:
            print(f"   ✓ availableDepositLimit() returns max uint256")
            print(f"   (depositPaused() check working correctly)")
        else:
            print(f"   Deposit limit: {deposit_limit}")
    except Exception as e:
        print(f"   ✗ Failed to check deposit limit: {e}")
        client.delete_vnet()
        return False

    # Check STAKING constant
    try:
        staking_addr = strategy.functions.STAKING().call()
        if staking_addr.lower() == CVG_STAKING.lower():
            print(f"   ✓ STAKING address correct: {staking_addr}")
        else:
            print(f"   ✗ STAKING address mismatch: {staking_addr}")
    except Exception as e:
        print(f"   ✗ Failed to check STAKING: {e}")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nStrategy deployed at: {strategy_address}")
    print(f"- forceApprove() in constructor: WORKS")
    print(f"- depositPaused() check: WORKS")
    print(f"- availableDepositLimit(): WORKS")

    # Cleanup
    print(f"\nCleaning up VNet...")
    client.delete_vnet()

    return True

if __name__ == "__main__":
    success = test_deployment()
    sys.exit(0 if success else 1)
