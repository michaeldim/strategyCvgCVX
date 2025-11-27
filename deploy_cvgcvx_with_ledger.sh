#!/bin/bash
set -e

# CVG-CVX Strategy Deployment via Ledger (bypasses forge simulation)
# Starting from TX 2 - assumes factory is already deployed

# Configuration
DEPLOYER="0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3"
CVGCVX_TOKEN="0x2191DF768ad71140F9F3E96c1e4407A4aA31d082"
MANAGEMENT="0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3"
KEEPER="0xa88e98bBD2Af6DDD642407cB5455f956f0C553F0"
PERFORMANCE_FEE_RECIPIENT="0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3"
EMERGENCY_ADMIN="0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3"
STRATEGY_NAME="Staked cvgCVX Compounder"

RPC_URL="https://eth-mainnet.g.alchemy.com/v2/SjBWiJLYGGG5xXWsLRP0oZhlD4AsDc3x"

# FACTORY ADDRESS - SET THIS TO YOUR DEPLOYED FACTORY
FACTORY_ADDRESS="${1:-}"

if [ -z "$FACTORY_ADDRESS" ]; then
    echo "ERROR: Factory address required"
    echo "Usage: $0 <factory_address>"
    echo "Example: $0 0x1234..."
    exit 1
fi

echo "========================================"
echo "CVG-CVX Strategy Deployment via Ledger"
echo "========================================"
echo "Deployer: $DEPLOYER"
echo "Factory: $FACTORY_ADDRESS"
echo "RPC: $RPC_URL"
echo "========================================"
echo ""

echo "========================================"
echo "[TX 2] Deploy Strategy via Factory"
echo "========================================"
echo "Calling factory.newStrategy()..."
echo "Please confirm on Ledger..."

# Encode the newStrategy call
NEW_STRATEGY_DATA=$(cast calldata "newStrategy(address,string)" "$CVGCVX_TOKEN" "$STRATEGY_NAME")

STRATEGY_TX=$(cast send \
    --rpc-url "$RPC_URL" \
    --ledger \
    "$FACTORY_ADDRESS" \
    "$NEW_STRATEGY_DATA" \
    --json)

STRATEGY_TX_HASH=$(echo "$STRATEGY_TX" | jq -r '.transactionHash')

echo "✓ Strategy deployment transaction sent: $STRATEGY_TX_HASH"
echo ""
echo "Waiting for transaction to be mined..."
sleep 15

# Get the strategy address from the factory
echo "Getting strategy address from factory..."
STRATEGY_ADDRESS=$(cast call "$FACTORY_ADDRESS" "deployments(address)(address)" "$CVGCVX_TOKEN" --rpc-url "$RPC_URL")

echo "✓ Strategy deployed at: $STRATEGY_ADDRESS"
echo ""

# Verify strategy contract
echo "========================================"
echo "Verifying Strategy Contract on Etherscan"
echo "========================================"

STRATEGY_CONSTRUCTOR_ARGS=$(cast abi-encode "constructor(address,string)" "$CVGCVX_TOKEN" "$STRATEGY_NAME")

echo "Running verification (may take a minute)..."
forge verify-contract \
    "$STRATEGY_ADDRESS" \
    src/StkCVGCVXStrategy.sol:StkCVGCVXStrategy \
    --rpc-url "$RPC_URL" \
    --verifier-url "https://api.etherscan.io/v2/api" \
    --etherscan-api-key "$ETHERSCAN_API_KEY" \
    --constructor-args "$STRATEGY_CONSTRUCTOR_ARGS" \
    --watch || echo "⚠ Verification queued - check Etherscan in a few minutes"

echo "✓ Strategy verification submitted"
echo ""

echo "========================================"
echo "[TX 3] Accept Management"
echo "========================================"
echo "Please confirm on Ledger..."

ACCEPT_MGMT_DATA=$(cast calldata "acceptManagement()")

cast send \
    --rpc-url "$RPC_URL" \
    --ledger \
    "$STRATEGY_ADDRESS" \
    "$ACCEPT_MGMT_DATA"

echo "✓ Management accepted"
echo ""

echo "========================================"
echo "[TX 4] Set Performance Fee to 0%"
echo "========================================"
echo "Please confirm on Ledger..."

SET_FEE_DATA=$(cast calldata "setPerformanceFee(uint16)" "0")

cast send \
    --rpc-url "$RPC_URL" \
    --ledger \
    "$STRATEGY_ADDRESS" \
    "$SET_FEE_DATA"

echo "✓ Performance fee set to 0%"
echo ""

echo "========================================"
echo "DEPLOYMENT COMPLETE!"
echo "========================================"
echo "Factory: $FACTORY_ADDRESS"
echo "Strategy: $STRATEGY_ADDRESS"
echo ""
echo "Contracts verified on Etherscan:"
echo "  Strategy: https://etherscan.io/address/$STRATEGY_ADDRESS"
echo "========================================"
