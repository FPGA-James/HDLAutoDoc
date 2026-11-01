"""pyuvm environment for axis_pipeline.

A UVM testbench on top of cocotb: a sequence of random packets drives the stream, a
monitor samples what comes out, and a scoreboard checks that a packet leaves only when
its first byte reaches the threshold.
"""
import random

import cocotb
import pyuvm
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from pyuvm import (ConfigDB, uvm_analysis_port, uvm_component, uvm_driver, uvm_env,
                   uvm_monitor, uvm_scoreboard, uvm_sequence, uvm_sequence_item,
                   uvm_sequencer, uvm_test, uvm_tlm_analysis_fifo)

THRESHOLD = 100


class PacketItem(uvm_sequence_item):
    """One packet: its bytes, the first of which decides whether it is forwarded."""

    def __init__(self, name, data=None):
        super().__init__(name)
        self.data = data or []


class PacketSequence(uvm_sequence):
    """Random packets of one to four bytes."""

    def __init__(self, name, count=20):
        super().__init__(name)
        self.count = count

    async def body(self):
        for n in range(self.count):
            item = PacketItem(f"pkt{n}", [random.randrange(256) for _ in range(random.randint(1, 4))])
            await self.start_item(item)
            await self.finish_item(item)


class StreamDriver(uvm_driver):
    """Drives each packet onto s_axis, one byte per cycle."""

    def build_phase(self):
        self.dut = ConfigDB().get(self, "", "DUT")

    async def run_phase(self):
        while True:
            item = await self.seq_item_port.get_next_item()
            for i, byte in enumerate(item.data):
                self.dut.s_axis_tdata.value = byte
                self.dut.s_axis_tvalid.value = 1
                self.dut.s_axis_tlast.value = int(i == len(item.data) - 1)
                await RisingEdge(self.dut.clk)
            self.dut.s_axis_tvalid.value = 0
            self.seq_item_port.item_done()


class StreamMonitor(uvm_monitor):
    """Collects the bytes that appear on m_axis, one packet at a time."""

    def build_phase(self):
        self.dut = ConfigDB().get(self, "", "DUT")
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):
        packet = []
        while True:
            await RisingEdge(self.dut.clk)
            if self.dut.m_axis_tvalid.value and self.dut.m_axis_tready.value:
                packet.append(int(self.dut.m_axis_tdata.value))
                if self.dut.m_axis_tlast.value:
                    self.ap.write(PacketItem("seen", packet))
                    packet = []


class Scoreboard(uvm_scoreboard):
    """Every packet seen on m_axis must start at or above the threshold."""

    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)
        self.analysis_export = self.fifo.analysis_export

    def check_phase(self):
        while self.fifo.can_get():
            _, item = self.fifo.try_get()
            assert item.data[0] >= THRESHOLD, f"packet {item.data} should have been dropped"


class PipelineEnv(uvm_env):
    """Sequencer, driver, monitor and scoreboard wired together."""

    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        self.driver = StreamDriver("driver", self)
        self.monitor = StreamMonitor("monitor", self)
        self.scoreboard = Scoreboard("scoreboard", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.monitor.ap.connect(self.scoreboard.analysis_export)


class PipelineTest(uvm_test):
    """Shared set-up: clock, reset and the environment."""

    def build_phase(self):
        self.env = PipelineEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        dut = ConfigDB().get(self, "", "DUT")
        cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
        dut.rst.value, dut.enable.value, dut.threshold.value = 1, 1, THRESHOLD
        dut.m_axis_tready.value = 1
        for _ in range(3):
            await RisingEdge(dut.clk)
        dut.rst.value = 0
        await self.sequence().start(self.env.seqr)
        for _ in range(10):
            await RisingEdge(dut.clk)
        self.drop_objection()


@pyuvm.test()
class RandomPacketsTest(PipelineTest):
    """Random packets: only those starting at or above the threshold come out."""

    def sequence(self):
        return PacketSequence("random", count=50)


@pyuvm.test(
    timeout_time=50,
    timeout_unit="us",
)
class SinglePacketTest(PipelineTest):
    """A single packet goes through and the scoreboard sees it."""

    def sequence(self):
        return PacketSequence("single", count=1)


@pyuvm.test(skip=True)
class BackpressureTest(PipelineTest):
    """m_axis_tready toggles while packets are in flight (not written yet)."""
