# Test Cases
This document describes the test cases covered by this unit testing infrastructure.

## Normal Operation
    1. Verify data transmitted through the slave interface is correctly received by a model UART receiver. If data isn't coming out at a rate we expect, the UART receiver should fail to receive the information correctly.
## Generic Checks
Run all [Normal Operation](#normal-operation) tests over a set of generics defined here.
    1. System clock less than 2 times the baud rate.
    2. System clock that is exactly 2 times the baud rate.
    3. Common system clock frequencies paired with common baud rates. Sprinkle different numbers of stop bits with different parity modes and different data bits widths throughout. Ensure to test the maximum total bit width with the fastest baud and slowest clock frequency.
## Assertion Checks
### Failures
    1. System clock frequency less than baud rate.
    2. Unsupported `PARITY_MODE` string.
### Warnings
    1. System clock frequency less than twice the baud rate.
    2. Large baud rate generator counter (e.g. `SYS_CLK_MHZ = 125.0` and `BAUD_RATE = 1`).
    3. Large difference in actual and expected baud (e.g. `SYS_CLK_MHZ = 25.0` and `BAUD_RATE = 230400`).