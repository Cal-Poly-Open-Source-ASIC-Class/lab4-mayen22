import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random


async def reset_dut(dut):
    """Applies async reset to both domains and stabilizes."""
    dut.i_wrst_n.value = 0
    dut.i_rrst_n.value = 0
    dut.i_wr_en.value = 0
    dut.i_rd_en.value = 0
    dut.i_wdata.value = 0
    await Timer(50, units='ns')
    dut.i_wrst_n.value = 1
    dut.i_rrst_n.value = 1
    for _ in range(2):
        await RisingEdge(dut.i_wclk)
        await RisingEdge(dut.i_rclk)


def get_fifo_config(dut):
    """Extracts DATA_WIDTH, ADDR_WIDTH, and FIFO_DEPTH from DUT."""
    DATA_WIDTH = len(dut.i_wdata)
    ADDR_WIDTH = len(dut.wbin) - 1
    FIFO_DEPTH = 2 ** ADDR_WIDTH
    return DATA_WIDTH, ADDR_WIDTH, FIFO_DEPTH


@cocotb.test()
async def test_fill_then_drain(dut):
    """Test fully filling FIFO from write domain and then draining from read domain"""

    cocotb.start_soon(Clock(dut.i_wclk, 10, units='ns').start())
    cocotb.start_soon(Clock(dut.i_rclk, 17, units='ns').start())

    await reset_dut(dut)
    DATA_WIDTH, ADDR_WIDTH, FIFO_DEPTH = get_fifo_config(dut)

    test_data = list(range(1, FIFO_DEPTH + 1))

    dut._log.info(f"FIFO depth: {FIFO_DEPTH}, Writing {len(test_data)} elements.")

    # === WRITE PHASE ===
    for val in test_data:
        while dut.o_wfull.value:
            await RisingEdge(dut.i_wclk)
        dut.i_wdata.value = val
        await RisingEdge(dut.i_wclk)
        dut.i_wr_en.value = 1
        await RisingEdge(dut.i_wclk)
        dut.i_wr_en.value = 0
        await RisingEdge(dut.i_wclk)

    # Wait a few extra cycles to allow o_wfull to assert
    for _ in range(5):
        if dut.o_wfull.value:
            break
        await RisingEdge(dut.i_wclk)

    assert dut.o_wfull.value == 1, "FIFO should be full after writing FIFO_DEPTH elements"

    # === READ PHASE ===
    read_data = []
    for _ in range(FIFO_DEPTH):
        while dut.o_rempty.value:
            await RisingEdge(dut.i_rclk)
        dut.i_rd_en.value = 1
        await RisingEdge(dut.i_rclk)
        read_data.append(int(dut.o_rdata.value))
        dut.i_rd_en.value = 0
        await RisingEdge(dut.i_rclk)

    # Wait for o_rempty to assert
    for _ in range(5):
        if dut.o_rempty.value:
            break
        await RisingEdge(dut.i_rclk)

    assert dut.o_rempty.value == 1, "FIFO should be empty after reading everything"
    assert read_data == test_data, f"Data mismatch!\nExpected: {test_data}\nGot: {read_data}"

@cocotb.test()
async def test_simultaneous_rw(dut):
    """Test simultaneous read/write operations with random data"""
    cocotb.start_soon(Clock(dut.i_rclk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.i_wclk, 7, units='ns').start())

    await reset_dut(dut)
    DATA_WIDTH, ADDR_WIDTH, FIFO_DEPTH = get_fifo_config(dut)

    data_to_write = [random.randint(1, 2**DATA_WIDTH - 1) for _ in range(FIFO_DEPTH * 2)]
    written = []
    read = []

    async def writer():
        for val in data_to_write:
            while dut.o_wfull.value:
                await RisingEdge(dut.i_wclk)
            dut.i_wdata.value = val
            await RisingEdge(dut.i_wclk)
            dut.i_wr_en.value = 1
            await RisingEdge(dut.i_wclk)
            dut.i_wr_en.value = 0
            written.append(val)
            await RisingEdge(dut.i_wclk)

    async def reader():
        read_cycles = 0
        while len(read) < len(data_to_write) and read_cycles < 500:
            await RisingEdge(dut.i_rclk)
            if not dut.o_rempty.value:
                dut.i_rd_en.value = 1
                await RisingEdge(dut.i_rclk)
                read.append(int(dut.o_rdata.value))
                dut.i_rd_en.value = 0
            read_cycles += 1

    await cocotb.start(writer())
    await reader()

    assert read == written, f"Simultaneous R/W failed\nExpected: {written}\nGot: {read}"




