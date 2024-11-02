from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import Timer, FallingEdge, RisingEdge, with_timeout
import cocotb
import os
import random


async def read_uart(
    dut, baud, data_bits_width=8, parity_mode="none", stop_bits_width=1
):
    """Read UART data from the DUT"""
    baud_period_ns = 1e9 / (baud)
    # Wait for the start bit.
    await FallingEdge(dut.out_tx)
    # Now wait for half of a full baud period to get in the middle of the start-bit
    await Timer(round(baud_period_ns / 2, 1), "ns")

    # Now just wait for a full baud period and take the value that came in as a data bit
    read_data = BinaryValue(0, data_bits_width)

    for bit_index in range(data_bits_width - 1, -1, -1):  # Note: The LSB comes in first
        await Timer(round(baud_period_ns, 1), "ns")
        read_data[bit_index] = dut.out_tx.value.integer
        dut._log.info(
            f"Reading bit {bit_index} of the UART transaction {dut.out_tx.value}"
        )

    if parity_mode != "none":
        # Grab the parity bit that comes out and ensure it's correct
        await Timer(round(baud_period_ns, 1), "ns")
        read_parity_bit = bool(dut.out_tx.value.integer)
        dut._log.info(
            f"Reading the parity bit of the UART transaction {int(read_parity_bit)}"
        )

        # Calculate even parity
        expected_parity_bit = False
        n = int(read_data)
        while n != 0:
            expected_parity_bit = not expected_parity_bit
            n = n & (n - 1)  # Unset the rightmost '1' from, n

        if parity_mode == "odd":
            # Flip the parity bit for what we expect
            expected_parity_bit = not expected_parity_bit
        elif parity_mode == "even":
            # Even parity is already what we calcuated
            pass
        else:
            assert False, "An unexpected parity mode is being used for this test."

        assert (
            read_parity_bit == expected_parity_bit
        ), f"The parity bit for this transaction doesn't check out. Expected: {int(expected_parity_bit)} Saw: {int(read_parity_bit)}"

    # Now make sure the stop bit came in
    await Timer(round(baud_period_ns, 1), "ns")
    assert dut.out_tx.value == 1, "No stop bit arrived for the UART transaction"

    if stop_bits_width > 1:
        # Make sure another stop bit came in
        await Timer(round(baud_period_ns, 1), "ns")
        assert (
            dut.out_tx.value == 1
        ), "The second stop bit never arrived for the UART transaction"

    # Return the data we read to the user
    return read_data


async def write_axi_stream(dut, data: BinaryValue | int | list[BinaryValue | int]):
    """Write data on the AXI-Stream-like interface of the DUT"""
    # Get in sync with the clock
    await RisingEdge(dut.clk)

    # Below allows a user to pass a list for data, such that transactions can be sent back to back
    if type(data) is list:
        dut._log.info("Starting burst transaction")
        data_buffer = data
    else:
        data_buffer = [data]

    dut._log.info(f"Here is the data buffer for a write: {data_buffer}")
    for d in data_buffer:
        # Note: "A Transmitter is not permitted to wait until TREADY is asserted before asserting TVALID"
        dut.in_valid.value = 1
        dut.in_data.value = d

        await RisingEdge(dut.clk)
        if dut.in_ready.value == 1:  # Check if the transaction took place off the bat
            pass  # Do nothing, the transaction took place and we're done.
        else:  # Otherwise just wait for the rising edge of the ready signal
            await RisingEdge(dut.in_ready)
            # The transaction will take place on the next clock edge
            await RisingEdge(dut.clk)

    # All transactions took place, de-assert valid
    dut.in_valid.value = 0


@cocotb.test()
async def normal_operation_test(dut):
    # Drive all input signals low to start
    dut.reset.value = 0
    dut.in_data.value = 0
    dut.in_valid.value = 0
    sys_clk = Clock(dut.clk, 8, "ns")  # 125 MHz clock
    await cocotb.start(sys_clk.start())

    # Reset the uut for a few clocks
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    for _ in range(2):
        await RisingEdge(dut.clk)

    # Gather the generics passed from the runner
    baud = int(os.getenv("BAUD_RATE"))
    data_bits_width = int(os.getenv("DATA_BITS_WIDTH"))
    parity_mode = os.getenv("PARITY_MODE")
    stop_bits_width = int(os.getenv("STOP_BITS_WIDTH"))

    async def single_transaction(val_to_send):
        data_in = BinaryValue(val_to_send, data_bits_width)
        reader = cocotb.start_soon(
            read_uart(dut, baud, data_bits_width, parity_mode, stop_bits_width)
        )
        writer = await cocotb.start(write_axi_stream(dut, data_in))

        await reader.join()
        data_out = reader.result()
        await writer.join()

        assert (
            data_in == data_out
        ), f"The data passed to the UART did not match the data read {data_in} != {data_out}"

    async def burst_transaction(vals_to_send):
        data_in_arr = [
            BinaryValue(val_to_send, data_bits_width) for val_to_send in vals_to_send
        ]
        writer = cocotb.start_soon(write_axi_stream(dut, data_in_arr))
        for data_in in data_in_arr:
            reader = await cocotb.start(
                read_uart(dut, baud, data_bits_width, parity_mode, stop_bits_width)
            )

            await reader.join()
            data_out = reader.result()

            assert (
                data_in == data_out
            ), f"The data passed to the UART did not match the data read {data_in} != {data_out}"

        await with_timeout(writer.join(), 1, "us")

    # Run a few singular transactions transaction
    num_single_transactions = 5
    dut._log.info(f"Testing {num_single_transactions} single transactions.")
    for val in [
        random.randint(0, 2**data_bits_width - 1)
        for _ in range(num_single_transactions)
    ]:
        await single_transaction(val)

    # Run a bulk transaction
    num_transactions_in_bulk = 10
    dut._log.info(
        f"Testing a bulk transaction with {num_transactions_in_bulk} transactions."
    )
    await burst_transaction(
        [
            random.randint(0, 2**data_bits_width - 1)
            for _ in range(num_transactions_in_bulk)
        ]
    )

    # Run edge case transactions
    await single_transaction(0xFF)
    await single_transaction(0x00)
