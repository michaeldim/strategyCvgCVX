# CVG cvgCVX Staking Contract - Function Parameters Explained

## Contract: `0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119`

---

## 📥 deposit() Function

### Function Signature
```solidity
function deposit(
    uint256 amountIn,
    uint8 inTokenType,
    uint256 minCvgCvxAmountOut,
    uint256 minCvxAmountOut,
    bool isLock
) external payable
```

### Parameters Explained

#### 1. `amountIn` (uint256)
**What**: The amount of tokens you're depositing
**Unit**: Wei (18 decimals for most tokens)
**Example**: `1000000000000000000` = 1 token
**Always Used**: ✅ YES - This is the core deposit amount

---

#### 2. `inTokenType` (uint8) - **CRITICAL PARAMETER**
**What**: Specifies which token you're depositing
**Values**:
- `0` = **cvgCVX** (direct deposit)
- `1` = **CVX** (Convex token)
- `2` = **CVX1** (wrapped CVX)
- `3` = **ETH** (Ethereum)

**Code Path by Type**:

**Type 0 (cvgCVX)** - Lines 145-148:
```solidity
cvgCVX.transferFrom(msg.sender, address(this), amountIn);
cvgCvxAmountToStake = amountIn;
```
- ✅ Direct 1:1 transfer
- ❌ NO swap
- ❌ NO minting
- ❌ NO fees

**Type 1 (CVX)** - Lines 150-161:
```solidity
if (minCvgCvxAmountOut != 0) {
    // Swap CVX → CVX1 → cvgCVX via Curve
    cvx1.mintFrom(msg.sender, address(this), amountIn);
    cvgCvxAmountToStake = curvePool.exchange(..., minCvgCvxAmountOut, ...);
} else {
    // Mint cvgCVX directly from CVX
    cvgCvxAmountToStake = cvgCVX.mintFrom(msg.sender, address(this), amountIn, isLock);
}
```
- Option A: Swap via Curve pool
- Option B: Mint cvgCVX (uses isLock parameter)

**Type 2 (CVX1)** - Lines 164-175:
```solidity
if (minCvgCvxAmountOut != 0) {
    // Swap CVX1 → cvgCVX via Curve
    cvx1.transferFrom(msg.sender, address(this), amountIn);
    cvgCvxAmountToStake = curvePool.exchange(..., minCvgCvxAmountOut, ...);
} else {
    // Unwrap CVX1 and mint cvgCVX
    cvx1.withdrawFrom(amountIn, msg.sender, address(cvgCVX));
    cvgCvxAmountToStake = cvgCVX.mintFrom(address(0), address(this), amountIn, isLock);
}
```

**Type 3 (ETH)** - Lines 177-194:
- Converts ETH to CVX first
- Then follows CVX path

---

#### 3. `minCvgCvxAmountOut` (uint256)
**What**: Minimum cvgCVX you expect to receive (slippage protection)
**When Used**:
- ✅ Type 1, 2, 3 **IF swapping via Curve pool**
- ❌ Type 0 (cvgCVX) - **IGNORED**
- ❌ Type 1, 2 if minting directly - **IGNORED**

**Purpose**: Protects against Curve pool slippage
**Example**: If depositing 1000 CVX, you might set `minCvgCvxAmountOut = 990e18` (99% of expected)

**For Our Strategy (Type 0)**:
- Parameter: **IGNORED** by code
- We pass: `0` (doesn't matter)

---

#### 4. `minCvxAmountOut` (uint256)
**What**: Minimum CVX expected from ETH conversion
**When Used**:
- ✅ Type 3 (ETH) only - line 179
- ❌ Type 0, 1, 2 - **IGNORED**

**Purpose**: Slippage protection when swapping ETH → CVX

**For Our Strategy (Type 0)**:
- Parameter: **IGNORED** by code
- We pass: `0` (doesn't matter)

---

#### 5. `isLock` (bool)
**What**: Whether to lock CVX in vlCVX (vote-locked CVX)
**When Used**:
- ✅ Type 1, 2, 3 **when minting** cvgCVX from CVX
- ❌ Type 0 (cvgCVX) - **IGNORED**
- ❌ Type 1, 2, 3 when swapping - **IGNORED**

**Impact on Fees** (for CVX deposits):
- `isLock = true`: **0% fee** (CVX locked in vlCVX)
- `isLock = false`: **0.25% fee** (CVX not locked)

**For Our Strategy (Type 0)**:
- Parameter: **IGNORED** by code (no minting happens)
- We pass: `false` (doesn't matter)

---

### Real Transaction Examples

**Example 1: cvgCVX Direct Deposit** (Our Strategy)
```
Transaction: 0x8117d952141a02d01e464485f94eaa82422ada21cc656d960d58d2dfd13ae8be
amountIn: 191.341730 cvgCVX
inTokenType: 0 (cvgCVX)
minCvgCvxAmountOut: 0
minCvxAmountOut: 0
isLock: true (ignored)

Result: 191.341730 cvgCVX staked (1:1, no fees, no swaps)
```

**Example 2: CVX1 Deposit with Swap**
```
Transaction: 0x0d59b495f8057b92815eb5895b300a1a5a79e870b71c2be9a24e0028b5ac8b36
amountIn: 6,893 CVX1
inTokenType: 2 (CVX1)
minCvgCvxAmountOut: 6,886.108536 (slippage protection)
minCvxAmountOut: 0 (not used for CVX1)
isLock: true (not used when swapping)

Result: 6,893.001538 cvgCVX (slight positive slippage!)
```

---

## 📤 withdraw() Function

### Function Signature
```solidity
function withdraw(
    uint256 amount,
    uint8 tokenType,
    uint256 minCvx1AmountOut
) external
```

### Parameters Explained

#### 1. `amount` (uint256)
**What**: Amount of staked cvgCVX to withdraw
**Unit**: Wei (18 decimals)
**Always Used**: ✅ YES - This is what you're unstaking

---

#### 2. `tokenType` (uint8) - **CRITICAL PARAMETER**
**What**: Specifies which token you want to receive
**Values**:
- `0` = **cvgCVX** (direct withdrawal)
- `1` = **CVX1** (swap to CVX1)
- `2` = **CVX** (swap to CVX1, then unwrap to CVX)

**Code Path by Type**:

**Type 0 (cvgCVX)** - Line 290:
```solidity
cvgCVX.transfer(msg.sender, amount);
```
- ✅ Direct 1:1 transfer
- ❌ NO swap
- ❌ NO slippage
- ❌ NO fees

**Type 1 (CVX1)** - Line 287:
```solidity
curvePool.exchange(1, 0, amount, minCvx1AmountOut, msg.sender);
```
- ✅ Swaps cvgCVX → CVX1 via Curve
- ⚠️ Subject to slippage
- ✅ Uses minCvx1AmountOut for protection

**Type 2 (CVX)** - Lines 279-282:
```solidity
uint256 exchangedAmount = curvePool.exchange(1, 0, amount, minCvx1AmountOut, address(this));
cvx1.withdraw(exchangedAmount, msg.sender);
```
- ✅ Swaps cvgCVX → CVX1 via Curve
- ✅ Unwraps CVX1 → CVX
- ⚠️ Subject to slippage
- ✅ Uses minCvx1AmountOut for protection

---

#### 3. `minCvx1AmountOut` (uint256)
**What**: Minimum CVX1 expected from Curve swap (slippage protection)
**When Used**:
- ✅ Type 1, 2 (swapping via Curve)
- ❌ Type 0 (cvgCVX) - **IGNORED** (direct transfer, no swap)

**Purpose**: Prevents sandwich attacks and excessive slippage on Curve

**For Our Strategy (Type 0)**:
- Parameter: **IGNORED** by code (no swap happens)
- We pass: `toWithdraw` (semantically correct: expect full amount back 1:1)
- Could also pass: `0` (doesn't matter, but less clear)

---

### Real Transaction Examples

**Example 1: cvgCVX Direct Withdrawal** (Our Strategy)
```
Transaction: 0x429aea05fe223483d012d804361f1c82279d75d24ba2361116460d7b20317e02
amount: 16,500 cvgCVX
tokenType: 0 (cvgCVX)
minCvx1AmountOut: 16,483.5 (99.9% - ignored but provided)

Result: 16,500 cvgCVX received (exact 1:1)
```

**Example 2: Withdraw to CVX**
```
Transaction: (hypothetical type 2)
amount: 1,000 cvgCVX
tokenType: 2 (CVX)
minCvx1AmountOut: 990e18 (99% slippage protection)

Flow:
1. Swap 1,000 cvgCVX → ~995 CVX1 (Curve pool)
2. Unwrap 995 CVX1 → 995 CVX
Result: ~995 CVX received (subject to Curve slippage)
```

---

## 🎯 Our Strategy's Parameter Choices

### deposit() - Type 0 (cvgCVX)
```solidity
STAKING.deposit(
    amount,          // ✅ Amount to deposit
    0,               // ✅ Type 0 = cvgCVX direct
    0,               // ❌ Ignored (no swap)
    0,               // ❌ Ignored (no ETH)
    false            // ❌ Ignored (no minting)
)
```

### withdraw() - Type 0 (cvgCVX)
```solidity
STAKING.withdraw(
    toWithdraw,      // ✅ Amount to withdraw
    0,               // ✅ Type 0 = cvgCVX direct
    toWithdraw       // ❌ Ignored but semantically correct (expect 1:1)
)
```

---

## 📊 Parameter Usage Matrix

| Function | Parameter | Type 0 (cvgCVX) | Type 1 (CVX) | Type 2 (CVX1) | Type 3 (ETH) |
|----------|-----------|-----------------|--------------|---------------|--------------|
| **deposit()** |
| amountIn | ✅ Used | ✅ Used | ✅ Used | ✅ Used |
| inTokenType | ✅ Used | ✅ Used | ✅ Used | ✅ Used |
| minCvgCvxAmountOut | ❌ Ignored | ✅ If swapping | ✅ If swapping | ✅ If swapping |
| minCvxAmountOut | ❌ Ignored | ❌ Ignored | ❌ Ignored | ✅ Used |
| isLock | ❌ Ignored | ✅ If minting | ✅ If minting | ✅ If minting |
| **withdraw()** |
| amount | ✅ Used | ✅ Used | ✅ Used | N/A |
| tokenType | ✅ Used | ✅ Used | ✅ Used | N/A |
| minCvx1AmountOut | ❌ Ignored | ✅ Used | ✅ Used | N/A |

---

## 🔑 Key Takeaways

### For cvgCVX Direct Operations (Type 0):

**deposit()**:
- Only `amountIn` and `inTokenType` matter
- All other parameters are **completely ignored**
- It's just a simple `transferFrom()` - no logic, no swaps, no fees

**withdraw()**:
- Only `amount` and `tokenType` matter
- `minCvx1AmountOut` is **completely ignored**
- It's just a simple `transfer()` - no logic, no swaps, no fees

### Why This Matters for Our Strategy:

✅ **Zero complexity** - Just token transfers
✅ **Zero slippage** - 1:1 in/out guaranteed
✅ **Zero fees** - No minting fees, no swap fees
✅ **Predictable gas** - No complex logic, fixed gas costs
✅ **No external dependencies** - No Curve pool, no oracle, no risk

This is why cvgCVX is the perfect asset for a simple auto-compounding strategy!
