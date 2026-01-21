# CVG Profit Unlock Time Configuration

## Overview

This document explains why both the vault and strategy need their `profitMaxUnlockTime` set to 14 days to align with the CVG (Convergence) reward cycle.

## Contracts

- **Vault**: `0x0849b046292293f78dF3002F8461f8A7e2eC2b82`
- **Strategy**: `0x8ED5AB1BA2b2E434361858cBD3CA9f374e8b0359`

## Current Settings

| Contract | Current profitMaxUnlockTime | Current (days) | Target | Target (days) |
|----------|----------------------------|----------------|---------|---------------|
| Vault    | 604,800 seconds            | 7 days         | 1,209,600 | 14 days    |
| Strategy | 864,000 seconds            | 10 days        | 1,209,600 | 14 days    |

## CVG Reward Cycle Mechanics

### Epoch Timing
- **Epoch Duration**: 1 week (604,800 seconds)
- **Epoch Start**: Every Thursday at 01:00 BST / 00:00 GMT
- **Current Cycle**: 90

### Reward Schedule (N+2 Cycle Delay)

```
Cycle N:   User stakes cvgCVX
           └─> Position is "pending" (not yet earning)

Cycle N+1: Position becomes "active" and accrues rewards
           └─> MUST remain staked for the entire epoch!

Cycle N+2: Rewards become claimable
           └─> User can claim rewards from Cycle N+1
```

**Key Rule**: Stakes must remain active for the **entire epoch** to be eligible for rewards.

**Total Time**: Minimum 2 full weeks (14 days) from stake to claim.

### Example Timeline

If you stake on Thursday, Oct 23 at 01:00:
- **Cycle 91 (Oct 23-30)**: Your stake is pending (not earning)
- **Cycle 92 (Oct 30-Nov 6)**: Your stake is active and accruing rewards
  - ⚠️ **MUST stay staked for all 7 days!**
- **Cycle 93 (Nov 6+)**: You can claim rewards earned in Cycle 92

## Why 14 Days for profitMaxUnlockTime?

### What is profitMaxUnlockTime?

`profitMaxUnlockTime` is a Yearn V3 parameter that controls how long profits are linearly unlocked over time. When the strategy reports profits:
- Profits unlock linearly over `profitMaxUnlockTime` period
- Share price increases gradually as profits unlock
- This prevents profit manipulation and frontrunning

### Why Align with CVG Cycle?

Setting `profitMaxUnlockTime` to 14 days aligns with CVG reward mechanics:

1. **Profit Reporting**: When the strategy harvests and reports CVG rewards, those profits unlock over 14 days
2. **Withdrawal Behavior**: If profitMaxUnlockTime is shorter than the CVG cycle:
   - User deposits before epoch N
   - Profits start unlocking
   - User could withdraw unlocked profits mid-epoch
   - Strategy loses CVG rewards (requires full epoch staking)
   - Other depositors are diluted

3. **Fair Distribution**: 14-day unlock ensures:
   - Profits unlock in sync with when they're actually claimable
   - No artificial advantages for short-term depositors
   - Better alignment with underlying reward mechanics

## Important Limitations

### profitMaxUnlockTime Only Locks Profits

**⚠️ Critical**: `profitMaxUnlockTime` only affects **profit** distribution, NOT principal!

Users can **always** withdraw their initial deposit, which means:
- A user deposits 100 cvgCVX at cycle N
- User can withdraw the 100 cvgCVX anytime (even mid-epoch)
- If withdrawn mid-epoch, the strategy loses CVG rewards
- Other depositors are diluted

### No Complete Protection

Setting profitMaxUnlockTime to 14 days provides:
- ✅ Aligns profit unlock with actual reward timing
- ✅ Prevents short-term profit frontrunning
- ❌ Does NOT prevent principal withdrawal mid-epoch
- ❌ Does NOT fully protect against reward dilution

## Why Update Both Vault and Strategy?

Users can deposit into either:

1. **Vault Directly** (`0x0849...2b82`)
   - Standard user path
   - Vault manages capital allocation to strategies
   - Vault's profitMaxUnlockTime affects profit distribution to vault depositors

2. **Strategy Directly** (`0x8ED5...0359`)
   - Advanced users can deposit directly into strategy
   - Strategy's profitMaxUnlockTime affects profit distribution to strategy depositors

**Both must be set to 14 days** to ensure consistent behavior regardless of deposit path.

## Management Addresses

To update these settings, you need access to:

| Contract | Function | Required Signer | Address |
|----------|----------|----------------|---------|
| Vault    | `setProfitMaxUnlockTime(uint256)` | Role Manager | `0x4b0a8e6170151f3797EEEDC043aC3Dd632C2Adef` |
| Strategy | `setProfitMaxUnlockTime(uint256)` | Management   | `0x7bdfE11c4981Dd4c33E1aa62457B8773253791b3` |

## Scripts

Three scripts are provided:

1. **`set-profit-unlock-time.sh`** - Updates strategy only (legacy)
2. **`set-vault-profit-unlock-time.sh`** - Updates vault only
3. **`set-all-profit-unlock-times.sh`** - Updates both (recommended)

### Usage

```bash
# Update both vault and strategy (recommended)
./set-all-profit-unlock-times.sh

# Or update individually
./set-vault-profit-unlock-time.sh
./set-profit-unlock-time.sh
```

All scripts use Ledger hardware wallet for signing.

## Verification

After updating, verify the new values:

```bash
# Check vault
cast call 0x0849b046292293f78dF3002F8461f8A7e2eC2b82 \
  "profitMaxUnlockTime()(uint256)" \
  --rpc-url $ETH_RPC_URL

# Check strategy
cast call 0x8ED5AB1BA2b2E434361858cBD3CA9f374e8b0359 \
  "profitMaxUnlockTime()(uint256)" \
  --rpc-url $ETH_RPC_URL
```

Both should return `1209600` (14 days in seconds).

## References

- [CVG Liquid Boost Documentation](https://docs-liquidboost.tangent.finance/vlcvx-wrapper/)
- [CVG Staking Contract](https://etherscan.io/address/0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119)
- [CVG Rewards Contract](https://etherscan.io/address/0xa044fd2E8254eC5DE93B15b8B27d005899579109)
- Vault: https://etherscan.io/address/0x0849b046292293f78dF3002F8461f8A7e2eC2b82
- Strategy: https://etherscan.io/address/0x8ED5AB1BA2b2E434361858cBD3CA9f374e8b0359
