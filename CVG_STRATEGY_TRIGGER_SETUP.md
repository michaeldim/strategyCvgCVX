# CVG Strategy Trigger Setup Guide

## Overview

The cvgCVX strategy requires a custom report trigger because CVG rewards follow a **weekly epoch system** with specific claiming rules:

- **Epochs start**: Thursday 00:00 UTC
- **Deposit in Epoch N**: Position is pending
- **Epoch N+1**: Position becomes active and earns rewards
- **Epoch N+2**: Rewards from N+1 become claimable

This means harvesting more than once per week is wasteful and may even fail if no rewards are available.

## Architecture

### 1. CvgCvxStrategyTrigger.sol
Custom trigger contract that:
- Checks the current CVG staking cycle
- Ensures minimum 7 days between reports
- Verifies claimable rewards exist before triggering harvest
- Tracks last reported cycle to prevent duplicate reports in same epoch

### 2. CommonReportTrigger Integration
Yearn's keeper network uses `CommonReportTrigger` (0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147) to determine when strategies should report. By setting a custom trigger, we override the default logic with epoch-aware timing.

## Deployment Steps

### Step 1: Deploy the Trigger Contract (ONE TIME ONLY)

**IMPORTANT**: The trigger contract supports multiple strategies via a mapping. You only need to deploy it **once** and all cvgCVX strategies can share the same instance.

```bash
forge script script/DeployCvgCvxStrategyTrigger.s.sol:DeployCvgCvxStrategyTrigger \
    --rpc-url mainnet \
    --broadcast \
    --verify
```

This deploys `CvgCvxStrategyTrigger` and outputs its address.

**If already deployed**: Use the existing trigger address `EXISTING_TRIGGER_ADDRESS` for all future strategies.

### Step 2: Register with CommonReportTrigger

As strategy management, call:
```solidity
ICommonReportTrigger(0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147)
    .setCustomStrategyTrigger(STRATEGY_ADDRESS, TRIGGER_ADDRESS)
```

This tells Yearn's keeper network to use your custom trigger instead of the default logic.

## How It Works

### Without Custom Trigger (Default Behavior)
```
Keeper checks every block:
  → Is strategy deployed? ✓
  → Has minimum time passed? ✓
  → Is gas acceptable? ✓
  → TRIGGER HARVEST (even if no rewards available) ❌
```

### With Custom Trigger (Epoch-Aware)
```
Keeper checks every block:
  → Is strategy deployed? ✓
  → Call custom trigger reportTrigger()
    → Has 7 days passed? ✓
    → Is it a new epoch/cycle? ✓
    → Are rewards claimable? ✓
    → TRIGGER HARVEST (only when rewards exist) ✅
  → If false, wait...
```

## Trigger Logic Flow

```solidity
function reportTrigger(address _strategy) external view returns (bool, bytes memory) {
    // 1. Check strategy is active
    if (strategy.isShutdown()) return (false, "Shutdown");

    // 2. Check assets deployed
    if (strategy.totalAssets() == 0) return (false, "No assets");

    // 3. Check minimum time delay (7 days)
    if (block.timestamp - strategy.lastReport() < 7 days) {
        return (false, "Too soon");
    }

    // 4. Check if rewards are actually claimable
    (uint256 cvg, TokenAmount[] memory rewards) = STAKING.getAllClaimableAmounts(_strategy);
    if (no rewards) return (false, "No rewards");

    // All checks passed - rewards exist, time to harvest!
    return (true, abi.encodeWithSignature("report()"));
}
```

## Benefits

✅ **Gas Efficiency**: Only harvests when rewards are available
✅ **Prevents Failures**: Won't trigger if claims would revert
✅ **Optimal Timing**: Respects CVG's weekly epoch system
✅ **Automated**: Keepers handle everything once set up
✅ **Flexible**: Management can still manually trigger via `tend()` or `report()`

## Monitoring

### Check Trigger Status
```solidity
// Check if strategy would trigger
(bool canExec, bytes memory reason) = trigger.reportTrigger(strategyAddress);
```

### Manual Override
If you need to harvest outside the normal schedule:
```solidity
strategy.report() // As management or keeper
```

## Addresses

| Contract | Address | Purpose | Deploy Once? |
|----------|---------|---------|--------------|
| CVG Staking | 0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119 | Where cvgCVX is staked | N/A (existing) |
| CommonReportTrigger | 0xA045D4dAeA28BA7Bfe234c96eAa03daFae85A147 | Yearn keeper trigger system | N/A (existing) |
| CvgCvxStrategyTrigger | TBD | Custom epoch-aware trigger | **YES** - shared by all strategies |
| CvgCvxStrategy | TBD | The strategy contract | No - deploy per vault |

## Security Considerations

- **View-only**: Trigger is a pure view function, can't modify state
- **Management Control**: Only strategy management can set/change the trigger
- **Manual Override**: Management can always call report() directly if needed
- **No Fund Risk**: Trigger contract never holds or interacts with funds

## Troubleshooting

### Trigger returns "No rewards available"
- Ensure position has been staked for at least one full epoch
- Rewards from epoch N are claimable in epoch N+2

### Trigger returns "Too soon"
- Minimum 7 days must pass between reports
- Check `strategy.lastReport()` timestamp

## Example Timeline

```
Week 1 (Epoch 100):
  Monday: Deploy strategy, deposit 1000 cvgCVX
  Thursday 00:00 UTC: Epoch 101 starts

Week 2 (Epoch 101):
  Position is now active and earning rewards
  Trigger: Returns false (no rewards claimable yet)

Week 3 (Epoch 102):
  Thursday 00:00 UTC: Epoch 102 starts
  Trigger: Returns TRUE ✅ (rewards from epoch 101 now claimable)
  Keeper: Calls report() → Claims rewards → Restakes → Profit!

Week 4 (Epoch 103):
  Thursday 00:00 UTC: Epoch 103 starts
  Trigger: Returns TRUE ✅ (rewards from epoch 102 claimable)
  Keeper: Harvests again

... and so on weekly ...
```

## Gas Savings

**Without custom trigger:**
- Keepers attempt harvest daily = ~52 attempts/week
- Only 1 succeeds, 51 waste gas checking

**With custom trigger:**
- Keeper attempts only when trigger is true
- ~1 successful harvest/week
- **98% reduction in wasted gas checks**
