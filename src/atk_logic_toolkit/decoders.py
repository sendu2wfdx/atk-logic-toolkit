from __future__ import annotations

from .analysis import edge_indices
from .capture import Capture


def _level_at(capture: Capture, channel: str, timestamp: float) -> int:
    times = capture.times
    lo, hi = 0, len(times)
    while lo < hi:
        mid = (lo + hi) // 2
        if times[mid] <= timestamp:
            lo = mid + 1
        else:
            hi = mid
    return capture.channels[channel][max(0, lo - 1)]


def decode_uart(capture: Capture, channel: str, baud: float, data_bits: int = 8, parity: str = "none", stop_bits: float = 1.0, inverted: bool = False) -> list[dict]:
    values = capture.channels[channel]
    if inverted:
        values = [1 - value for value in values]
    bit_time = 1.0 / baud
    frames = []
    last_end = float("-inf")
    for index in edge_indices(values, False):
        start = capture.times[index]
        if start < last_end:
            continue
        bits = []
        for bit in range(data_bits):
            value = _level_at(capture, channel, start + (1.5 + bit) * bit_time)
            bits.append(1 - value if inverted else value)
        value = sum(bit << n for n, bit in enumerate(bits))
        parity_error = False
        parity_bits = 0 if parity == "none" else 1
        if parity_bits:
            observed = _level_at(capture, channel, start + (1.5 + data_bits) * bit_time)
            if inverted:
                observed = 1 - observed
            expected = sum(bits) & 1
            if parity == "even":
                parity_error = observed != expected
            elif parity == "odd":
                parity_error = observed == expected
        stop_time = start + (1.5 + data_bits + parity_bits) * bit_time
        stop_level = _level_at(capture, channel, stop_time)
        if inverted:
            stop_level = 1 - stop_level
        frames.append({"time_s": start, "value": value, "hex": f"0x{value:02X}", "ascii": chr(value) if 32 <= value < 127 else None, "parity_error": parity_error, "framing_error": stop_level != 1})
        last_end = start + (1 + data_bits + parity_bits + stop_bits) * bit_time
    return frames


def decode_i2c(capture: Capture, scl: str, sda: str) -> list[dict]:
    clock, data = capture.channels[scl], capture.channels[sda]
    events = []
    active = False
    bits: list[int] = []
    start_time = 0.0
    for i in range(1, len(capture.times)):
        if clock[i] == 1 and data[i] != data[i - 1]:
            if data[i] == 0:
                if active and bits:
                    events.append(_i2c_transaction(start_time, capture.times[i], bits, repeated=True))
                active, bits, start_time = True, [], capture.times[i]
                events.append({"type": "start", "time_s": capture.times[i], "repeated": len(events) > 0})
            elif active:
                events.append(_i2c_transaction(start_time, capture.times[i], bits))
                events.append({"type": "stop", "time_s": capture.times[i]})
                active, bits = False, []
        if active and clock[i - 1] == 0 and clock[i] == 1:
            bits.append(data[i])
    if active and bits:
        events.append(_i2c_transaction(start_time, capture.times[-1], bits, incomplete=True))
    return events


def _i2c_transaction(start: float, end: float, bits: list[int], repeated: bool = False, incomplete: bool = False) -> dict:
    words = []
    for offset in range(0, len(bits) - 8, 9):
        byte_bits = bits[offset:offset + 8]
        value = sum(bit << (7 - n) for n, bit in enumerate(byte_bits))
        words.append({"value": value, "hex": f"0x{value:02X}", "ack": bits[offset + 8] == 0})
    result = {"type": "transaction", "start_s": start, "end_s": end, "bytes": words, "trailing_bits": len(bits) % 9}
    if words:
        result["address"] = words[0]["value"] >> 1
        result["direction"] = "read" if words[0]["value"] & 1 else "write"
    if repeated:
        result["ended_by_repeated_start"] = True
    if incomplete:
        result["incomplete"] = True
    return result


def decode_spi(capture: Capture, clk: str, mosi: str | None, miso: str | None, cs: str | None, mode: int = 0, lsb_first: bool = False, cs_active: int = 0, word_bits: int = 8) -> list[dict]:
    if mode not in range(4):
        raise ValueError("SPI mode must be 0, 1, 2, or 3")
    sample_rising = mode in (0, 3)
    edges = edge_indices(capture.channels[clk], sample_rising)
    transactions, current = [], []
    for index in edges:
        timestamp = capture.times[index]
        selected = cs is None or capture.channels[cs][index] == cs_active
        if not selected:
            if current:
                transactions.append(_spi_words(current, word_bits, lsb_first))
                current = []
            continue
        current.append((timestamp, capture.channels[mosi][index] if mosi else None, capture.channels[miso][index] if miso else None))
    if current:
        transactions.append(_spi_words(current, word_bits, lsb_first))
    return transactions


def _spi_words(samples: list[tuple[float, int | None, int | None]], width: int, lsb_first: bool) -> dict:
    def pack(bits: list[int]) -> int:
        return sum(bit << n for n, bit in enumerate(bits)) if lsb_first else sum(bit << (len(bits) - 1 - n) for n, bit in enumerate(bits))
    result = {"start_s": samples[0][0], "end_s": samples[-1][0], "words": []}
    for offset in range(0, len(samples) - width + 1, width):
        chunk = samples[offset:offset + width]
        word = {"time_s": chunk[0][0]}
        if chunk[0][1] is not None:
            value = pack([item[1] for item in chunk])
            word.update({"mosi": value, "mosi_hex": f"0x{value:0{(width + 3) // 4}X}"})
        if chunk[0][2] is not None:
            value = pack([item[2] for item in chunk])
            word.update({"miso": value, "miso_hex": f"0x{value:0{(width + 3) // 4}X}"})
        result["words"].append(word)
    result["trailing_bits"] = len(samples) % width
    return result

