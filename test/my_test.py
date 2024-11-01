import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer, FallingEdge, RisingEdge
from cocotb.clock import Clock

async def generate_clock(dut):
    """Generate clock pulses."""

    for cycle in range(10):
        dut.clk.value = 0
        await Timer(1, units="ns")
        dut.clk.value = 1
        await Timer(1, units="ns")

async def read_uart(dut, baud):
    """ Read UART data from the DUT """
    baud_period_ns = 1e9 / (baud)
    # Wait for the start bit.
    await FallingEdge(dut.out_tx)
    # Now wait for half of a full baud period to get in the middle of the start-bit
    await Timer(round(baud_period_ns/2, 1), "ns")


    # Now just wait for a full baud period and take the value that came in as a data bit
    read_data = BinaryValue(0, 8) # 8 bits of data

    for bit_index in range(7, -1, -1): # Note: The LSB comes in first
        await Timer(round(baud_period_ns, 1), "ns")
        read_data[bit_index] = dut.out_tx.value.integer
        dut._log.info(f"Reading bit {bit_index} of the UART transaction {dut.out_tx.value}")

    # Now make sure the stop bit came in
    await Timer(round(baud_period_ns, 1), "ns")
    assert dut.out_tx.value == 1, "No stop bit arrived for the UART transaction"

    # Return the data we read to the user
    return read_data

async def write_axi_stream(dut, data: BinaryValue | int):
    """ Write data on the AXI-Stream-like interface of the DUT"""
    # Get in sync with the clock
    await RisingEdge(dut.clk)
    # Note: "A Transmitter is not permitted to wait until TREADY is asserted before asserting TVALID"
    dut.in_valid.value = 1
    dut.in_data.value = data

    await RisingEdge(dut.clk)
    if dut.in_ready.value == 1: # Check if the transaction took place off the bat
        pass # Do nothing, the transaction took place and we're done.
    else: # Otherwise just wait for the rising edge of the ready signal
        await RisingEdge(dut.in_ready)
        # The transaction will take place on the next clock edge
        await RisingEdge(dut.clk)

    # The transaction took place, de-assert valid
    dut.in_valid.value = 0


@cocotb.test()
async def t1(dut):
    # Drive all input signals low to start
    dut.reset.value = 0
    dut.in_data.value = 0
    dut.in_valid.value = 0
    sys_clk = Clock(dut.clk, 8, "ns") # 125 MHz clock
    await cocotb.start(sys_clk.start())

    # Reset the uut for a few clocks
    for _ in range(2): await RisingEdge(dut.clk)
    dut.reset.value = 1
    for _ in range(2): await RisingEdge(dut.clk)
    dut.reset.value = 0
    for _ in range(2): await RisingEdge(dut.clk)

    # Run a transaction
    data_in = BinaryValue("01010101")
    reader = cocotb.start_soon(read_uart(dut, baud=115200))
    writer = await cocotb.start(write_axi_stream(dut, data_in))

    await reader.join()
    data_out = reader.result()

    assert data_in == data_out, f"The data passed to the UART did not match the data read {data_in} != {data_out}"

    # Run another
    data_in = BinaryValue("10101010")
    reader = cocotb.start_soon(read_uart(dut, baud=115200))
    writer = await cocotb.start(write_axi_stream(dut, data_in))

    await reader.join()
    data_out = reader.result()

    assert data_in == data_out, f"The data passed to the UART did not match the data read {data_in} != {data_out}"




# @cocotb.test()
# async def my_first_test(dut):
#     """Try accessing the design."""

#     for cycle in range(10):
#         dut.clk.value = 0
#         await Timer(1, units="ns")
#         dut.clk.value = 1
#         await Timer(1, units="ns")

#     dut._log.info("sig1 is %s", dut.sig1.value)
#     dut._log.info("sig2 is %s", dut.sig2.value)
#     # assert dut.sig2.value[0] == 0, "sig2[0] is not 0!"

# @cocotb.test()
# async def my_second_test(dut):
#     """Try accessing the design."""

#     sys_clk = Clock(dut.clk, 2, "ns")
#     await cocotb.start(sys_clk.start())  # run the clock "in the background"

#     await Timer(5, units="ns")  # wait a bit
#     await FallingEdge(dut.clk)  # wait for falling edge/"negedge"
#     dut._log.info(f"sig2 is {dut.sig2.value}")
#     await Timer(1, units="fs")
#     dut._log.info(f"sig2 is {dut.sig2.value}")
#     await RisingEdge(dut.clk)
#     dut._log.info(f"sig2 is {dut.sig2.value}")
#     await Timer(1, units="fs")
#     dut._log.info(f"sig2 is {dut.sig2.value}")

    # dut._log.info("my_signal_1 is %s", dut.my_signal_1.value)
    # assert dut.my_signal_2.value[0] == 0, "my_signal_2[0] is not 0!"