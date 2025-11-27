// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.23;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ICvgCvxStaking
 * @notice Interface for CVG cvgCVX Staking Position Service
 * @dev Contract: 0x2c1D293c50C6d1a4370ebb442A02c5956bbAb119
 */
interface ICvgCvxStaking {
    // Enums
    enum IN_TOKEN_TYPE {
        cvgCVX, // 0
        CVX, // 1
        CVX1, // 2
        ETH // 3
    }

    enum OUT_TOKEN_TYPE {
        cvgCVX, // 0
        CVX1, // 1
        CVX // 2
    }

    struct TokenAmount {
        IERC20 token;
        uint256 amount;
    }

    // Events
    event Deposit(
        address indexed user,
        uint256 indexed cycleId,
        uint256 amount
    );
    event Withdraw(
        address indexed user,
        uint256 indexed cycleId,
        uint256 amount
    );

    // Core functions
    function deposit(
        uint256 amountIn,
        IN_TOKEN_TYPE inTokenType,
        uint256 minCvgCvxAmountOut,
        uint256 minCvxAmountOut,
        bool isLock
    ) external payable;

    function withdraw(
        uint256 amount,
        OUT_TOKEN_TYPE tokenType,
        uint256 minCvx1AmountOut
    ) external;

    function claimCvgRewards(address account) external;
    function claimCvgCvxRewards(
        address account,
        uint256 minCvgCvxAmountOut,
        bool isConvert
    ) external;
    function claimCvgCvxMultiple(
        address operator
    ) external returns (uint256, TokenAmount[] memory);
    function getAllClaimableAmounts(
        address account
    ) external view returns (uint256, TokenAmount[] memory);

    // State views
    function balanceOf(address account) external view returns (uint256);
    function stakingCycle() external view returns (uint256);
    function depositPaused() external view returns (bool);

    // Getters
    function cvgCVX() external view returns (address);
    function cvx1() external view returns (address);
    function CVX() external view returns (address);
}
