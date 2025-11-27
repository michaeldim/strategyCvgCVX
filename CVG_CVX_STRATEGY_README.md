# CVG cvgCVX Staking Strategy

## Overview

A Yearn V3 tokenized strategy that stakes cvgCVX in the CVG protocol's staking contract and auto-compounds rewards.

**Key Insight**: Rewards ARE cvgCVX (the same as the underlying asset), making this an elegant auto-compounding strategy with **no swaps**, **no slippage**, and **no fees**.

## Contract Addresses

| Contract | Address | Description |
|----------|---------|-------------|
| cvgCVX Token | `0x2191DF768ad71140F9F3E96c1e4407A4aA31d082` | Underlying asset |
| Staking Contract | `0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119` | CVG cvgCVX Staking Position Service |
| CVX Token | `0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B` | Convex token |

## Strategy Mechanics

### Deposit Flow
1. User deposits cvgCVX to vault
2. Strategy stakes cvgCVX in CVG staking contract
3. Strategy tracks staked position (SCVGCVX balance)

**Zero Fees**: Depositing cvgCVX directly avoids the 0.25% mint fee that applies when depositing CVX without locking.

### Harvest Flow
1. Claim cvgCVX rewards from staking contract
2. Immediately restake claimed cvgCVX
3. Report total assets = staked + idle balance

**Critical Accounting**: Since rewards = asset, we MUST claim and restake in the same transaction to prevent the vault from treating unstaked rewards as "new profit".

### Withdraw Flow
1. Unstake requested amount from staking contract
2. Receive cvgCVX 1:1 (no slippage, no fees)
3. Return cvgCVX to vault

## CVG Cycle System

CVG operates on a weekly cycle system:

- **Cycle Duration**: 1 week (7 days)
- **Cycle Start**: Thursday 00:00 UTC
- **TDE Start**: February 1, 2024 (Cycle 1)
- **Current Cycle**: 90 (as of Oct 17, 2025)

### Reward Eligibility

- Deposits made in Cycle N are **PENDING** in Cycle N
- They become **ACTIVE** and start earning rewards in Cycle N+1
- Must be staked for a **FULL cycle** to earn rewards

**Example**:
- Deposit on Oct 16, 2025 (during Cycle 90)
- Status in Cycle 90: PENDING (not earning)
- Starts earning: Cycle 91 (Oct 23, 2025)

## Strategy Benefits

### No Fees
- ✅ **0% mint fee** (avoided by depositing cvgCVX directly)
- ✅ **0% withdrawal fee** (withdraw as cvgCVX)
- ✅ **0% swap fees** (no swaps needed)
- ✅ **0% slippage** (1:1 deposit/withdraw)

### No Complexity
- ✅ **No auctions needed** (rewards = asset)
- ✅ **No DEX integrations** (no swaps)
- ✅ **No oracle dependencies**
- ✅ **Simple accounting** (just track staked balance)

### Auto-Compounding
- Automatically claims cvgCVX rewards
- Immediately restakes for compound growth
- Gas-efficient harvesting

## Deployment

### Prerequisites
```bash
# Set environment variables
export PRIVATE_KEY=<your_private_key>
export ETH_RPC_URL=<your_rpc_url>
```

### Deploy via Factory
```bash
forge script script/DeployCvgCvxStrategy.s.sol:DeployCvgCvxStrategy \
    --rpc-url $ETH_RPC_URL \
    --broadcast \
    --verify
```

### Deploy with Ledger
```bash
forge script script/DeployCvgCvxStrategy.s.sol:DeployCvgCvxStrategy \
    --rpc-url $ETH_RPC_URL \
    --ledger \
    --sender <your_ledger_address> \
    --broadcast
```

## Testing

Run the test suite:
```bash
forge test --match-contract CvgCvxStrategyTest -vv
```

Run specific test:
```bash
forge test --match-test testFullCycleDepositHarvestWithdraw -vvv
```

## Integration with Vault

1. **Deploy or use existing vault** for cvgCVX
2. **Add strategy to vault**:
   ```solidity
   vault.add_strategy(strategyAddress)
   ```
3. **Set debt ratio**:
   ```solidity
   vault.update_max_debt_for_strategy(strategyAddress, 10_000) // 100%
   ```

## Management Functions

### Keeper Functions
- `harvest()` - Claims and restakes rewards (called by keeper bot)

### Management Functions
- `manualClaimRewards()` - Force claim if automatic fails
- `manualRestake()` - Force restake of idle cvgCVX
- `emergencyWithdraw()` - Emergency unstake (shutdown only)

## Key Differences from Other Strategies

### vs. StCVXCRV Strategy
| Feature | cvgCVX Strategy | StCVXCRV Strategy |
|---------|-----------------|-------------------|
| Rewards | cvgCVX (= asset) | CRV, CVX, crvUSD |
| Auctions | None needed | Yes, for reward swaps |
| Swaps | None | Yes, via auctions |
| Complexity | Low | Medium |
| Gas Cost | Lower | Higher |

### Accounting Simplicity
Traditional strategies:
```
Deposit X → Stake X → Earn Y (different token) → Swap Y to X → Stake again
```

This strategy:
```
Deposit X → Stake X → Earn X → Stake X again
```

## Security Considerations

1. **No External Dependencies**: No DEX, no oracle, no auction contracts
2. **Simple Logic**: Fewer attack vectors
3. **Direct Interactions**: Only with audited CVG staking contract
4. **Transparent Accounting**: Rewards = asset makes accounting obvious

## Gas Optimization

- Single approval in constructor (max approval)
- Minimal state changes during harvest
- No complex swap routing
- No auction mechanism overhead

## Resources

- [CVG Documentation](https://docs.cvg.finance/)
- [cvgCVX Token](https://etherscan.io/address/0x2191DF768ad71140F9F3E96c1e4407A4aA31d082)
- [Staking Contract](https://etherscan.io/address/0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119)
- [Yearn V3 Docs](https://docs.yearn.fi/developers/v3/overview)

## License

AGPL-3.0
