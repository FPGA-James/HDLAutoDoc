"""Register file tests for axil_regs.

Drives the AXI4-Lite port with single reads and writes and checks each register
against the map in registers/regs_axil_regs.toml.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CTRL, STATUS, THRESHOLD, SCRATCH, COUNT = 0x00, 0x04, 0x08, 0x0C, 0x10


async def axil_write(dut, addr, value):
    """Single AXI4-Lite write; waits for the response."""
    dut.s_axil_awaddr.value, dut.s_axil_wdata.value = addr, value
    dut.s_axil_awvalid.value = dut.s_axil_wvalid.value = 1
    await RisingEdge(dut.clk)
    dut.s_axil_awvalid.value = dut.s_axil_wvalid.value = 0
    dut.s_axil_bready.value = 1
    await RisingEdge(dut.clk)


async def axil_read(dut, addr):
    """Single AXI4-Lite read; returns the data."""
    dut.s_axil_araddr.value, dut.s_axil_arvalid.value = addr, 1
    await RisingEdge(dut.clk)
    dut.s_axil_arvalid.value, dut.s_axil_rready.value = 0, 1
    await RisingEdge(dut.clk)
    return int(dut.s_axil_rdata.value)


@cocotb.test()
async def reset_values(dut):
    """Every register reads back zero after reset.

    The count is zero until a filter forwards a packet.
    """
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    for addr in (CTRL, STATUS, THRESHOLD, SCRATCH, COUNT):
        assert await axil_read(dut, addr) == 0


@cocotb.test(
    timeout_time=10,
    timeout_unit="us",
)
async def scratch_write_read(dut):
    """A value written to the scratch register reads back unchanged."""
    await axil_write(dut, SCRATCH, 0xA5A5A5A5)
    assert await axil_read(dut, SCRATCH) == 0xA5A5A5A5


@cocotb.test(skip=True)
async def start_runs_a_capture(dut):
    """Setting ctrl.start moves the status to running (needs the full top level)."""
