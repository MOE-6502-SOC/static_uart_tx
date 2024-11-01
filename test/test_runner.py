import os
import subprocess
from pathlib import Path
from math import log2

import cocotb
import cocotb.regression
from cocotb.runner import get_runner

import cocotb.triggers
import pytest


def test_normal_operation():
    sim = os.getenv("SIM", "ghdl")

    # Gather sources from bender
    sources = subprocess.run(
        ["bender", "script", "flist", "-t", "simulation"],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.split()

    hdl_toplevel = "static_uart_tx"

    runner = get_runner(sim)
    runner.build(
        hdl_library="work",
        sources=sources,
        hdl_toplevel=hdl_toplevel,
    )

    # TODO: Implement the generic tests through pytest parametrize (this will involve making a little function too)
    test_args = ["-gBAUD_RATE=115200"]
    if os.getenv("WAVE") == 1:
        test_args.extend(["--wave", f"{runner.build_dir}/wave.ghw"])

    runner.test(
        hdl_toplevel_library="work",
        hdl_toplevel=hdl_toplevel,
        test_module="my_test",
        plusargs=test_args,
    )


"""
Assertion tests
"""


@cocotb.test()
async def coco_generic_properties_test(dut):
    try:
        await cocotb.triggers.Timer(1, units="ns")
        print("I'm still alive")
        pass
    except:
        print("An exception occured that I was expecting")


@pytest.mark.parametrize(
    (
        "sys_clk_hz",
        "baud_rate",
        "data_bits_width",
        "parity_mode",
        "stop_bits_width",
        "assertion_level",
        "assertion_message",
    ),
    (
        # System clock less than baud rate
        (
            7_000_000,
            7372800,
            8,
            "none",
            1,
            "error",
            "The system clock frequency must be greater than the baud rate for baud rate generation to work.",
        ),
        # Unsupported `PARITY_MODE` string
        (125_000_000, 115200, 8, "na", 1, "error", "Unknown PARITY_MODE: 'na'."),
        # System clock frequency less than twice the baud rate
        (
            10_000_000,
            7372800,
            8,
            "none",
            1,
            "warning",
            "The system clock frequency is not at least double the baud rate. This will cause an extra stop bit to be sent after each transaction.",
        ),
        # Large baud rate generator counter.
        (
            125_000_000,
            1,
            8,
            "none",
            1,
            "warning",
            f"A {int(round(log2(125_000_000)))} bit counter is necessary to implement a divisior of 1.25e8. Are your design parameters correct?",
        ),
        # Large difference in actual and expected baud.
        (25_000_000, 1843200, 8, "none", 1, "warning", "The generated baud rate diverges "),
    ),
)
def test_assertion_failures(
    capfd,
    sys_clk_hz: float,
    baud_rate: int,
    data_bits_width: int,
    parity_mode: str,
    stop_bits_width: int,
    assertion_level: str,
    assertion_message: str,
) -> None:
    sim = os.getenv("SIM", "ghdl")

    # Gather sources from bender
    sources = subprocess.run(
        ["bender", "script", "flist", "-t", "simulation"],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.split()

    hdl_toplevel = "static_uart_tx"

    runner = get_runner(sim)
    runner.build(
        hdl_library="work",
        sources=sources,
        hdl_toplevel=hdl_toplevel,
    )

    generics = {
        "SYS_CLK_HZ": sys_clk_hz,
        "BAUD_RATE": baud_rate,
        "DATA_BITS_WIDTH": data_bits_width,
        "PARITY_MODE": parity_mode,
        "STOP_BITS_WIDTH": stop_bits_width,
    }

    def generate_generics_args_ghdl(generics: dict[str, any]) -> list[str]:
        ghdl_generic_argument_list = []
        for generic, value in generics.items():
            ghdl_generic_argument_list.append(f"-g{generic}={value}")
        return ghdl_generic_argument_list

    test_args = []
    test_args.extend(generate_generics_args_ghdl(generics))
    if os.getenv("WAVE") == 1:
        test_args.extend(["--wave", f"{runner.build_dir}/wave.ghw"])

    runner.test(
        hdl_toplevel_library="work",
        hdl_toplevel=hdl_toplevel,
        test_module="test_runner",
        testcase="coco_generic_properties_test",
        plusargs=test_args,
    )
    # Ensure the assertion at the expected level fired, which is logged by the simulator at the file descriptor stdout level
    captured_output = capfd.readouterr()
    if f"(assertion {assertion_level}): {assertion_message}" not in captured_output.out:
        print("\nSTDOUT CAPTURED:")
        print(captured_output.out)
        print("\nSTDERR CAPTRUED:")
        print(captured_output.err)
        assert False, "The expected assertion was not seen in the standard output."


if __name__ == "__main__":
    print("Don't call me directly. Use `pytest`.")
