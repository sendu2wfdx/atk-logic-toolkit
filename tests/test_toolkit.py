from pathlib import Path

from atk_logic_toolkit.capture import Capture, load_csv
from atk_logic_toolkit.decoders import decode_i2c, decode_spi, decode_uart
from atk_logic_toolkit.hardware import CaptureConfig, _command, _configuration, _crc32_atk, _deinterleave_from_device, _instant_trigger, _interleave_for_device, parse_channels, parse_duration, parse_rate
from atk_logic_toolkit.profiles import PROFILES, profile_for_identity, profile_for_level


def sampled(lines, rate=1_000_000):
    times, channels = [], {name: [] for name in lines}
    count = len(next(iter(lines.values())))
    for i in range(count):
        times.append(i / rate)
        for name, values in lines.items():
            channels[name].append(values[i])
    return Capture(times, channels)


def test_csv_units(tmp_path: Path):
    path = tmp_path / "capture.csv"
    path.write_text("Time[us],D0,D1\n0,0,1\n2,1,1\n", encoding="utf-8")
    capture = load_csv(path)
    assert capture.times == [0.0, 2e-6]
    assert capture.channels["D0"] == [0, 1]


def test_uart_8n1():
    baud, rate, value = 10_000, 1_000_000, 0x55
    levels = [1] * 200
    bits = [0] + [(value >> bit) & 1 for bit in range(8)] + [1]
    for bit_index, level in enumerate(bits):
        start = 20 + bit_index * (rate // baud)
        levels[start:start + rate // baud] = [level] * (rate // baud)
    capture = sampled({"D0": levels}, rate)
    frames = decode_uart(capture, "D0", baud)
    assert frames[0]["value"] == value
    assert not frames[0]["framing_error"]


def test_i2c_address_and_byte():
    scl, sda = [1], [1]
    def add(c, d):
        scl.extend(c); sda.extend(d)
    add([1], [0])
    for byte in (0xA0, 0x33):
        for bit in [(byte >> shift) & 1 for shift in range(7, -1, -1)] + [0]:
            add([0, 1], [bit, bit])
    add([0, 1, 1], [0, 0, 1])
    events = decode_i2c(sampled({"SCL": scl, "SDA": sda}), "SCL", "SDA")
    transaction = next(item for item in events if item["type"] == "transaction")
    assert transaction["address"] == 0x50
    assert [item["value"] for item in transaction["bytes"]] == [0xA0, 0x33]


def test_spi_mode_zero():
    clk, mosi, cs = [0], [0], [1]
    cs.append(0); clk.append(0); mosi.append(0)
    for bit in [(0xA5 >> shift) & 1 for shift in range(7, -1, -1)]:
        clk.extend([0, 1, 0]); mosi.extend([bit, bit, bit]); cs.extend([0, 0, 0])
    cs.append(1); clk.append(0); mosi.append(0)
    transactions = decode_spi(sampled({"CLK": clk, "MOSI": mosi, "CS": cs}), "CLK", "MOSI", None, "CS")
    assert transactions[0]["words"][0]["mosi"] == 0xA5


def test_usb_lane_transform_round_trip():
    source = bytes((index * 17) & 0xFF for index in range(4096))
    assert _deinterleave_from_device(_interleave_for_device(source)) == source


def test_command_and_configuration_fixture():
    config = CaptureConfig([0, 1, 15], 20_000_000, 0.01, 1.6)
    payload = _configuration(config)
    assert payload[:3] == bytes((0x80, 16, 6))
    assert int.from_bytes(payload[3:8], "little") == 200_000
    frame = _deinterleave_from_device(_command(0x11, payload))
    assert frame[8:11] == bytes((0x0A, 0x11, len(payload) + 1))
    assert _crc32_atk(b"") == 0xFFFFFFFF


def test_human_units():
    assert parse_rate("20MHz") == 20_000_000
    assert parse_duration("10ms") == 0.01
    assert parse_channels("D15,0,D1") == [0, 1, 15]


def test_mcu_wakeup_frame_shape():
    class FakeDevice:
        def __init__(self): self.value = None
        def write(self, endpoint, value, timeout): self.value = bytes(value); return len(value)
    from atk_logic_toolkit.hardware import ATKLogicDevice
    fake = FakeDevice()
    instance = object.__new__(ATKLogicDevice); instance.device = fake
    instance.send_mcu(0x87, b"\x01")
    assert len(fake.value) == 512
    assert fake.value[:3] == b"\x0a\x87\x01"


def test_signal_generator_command_payload():
    from atk_logic_toolkit.hardware import ATKLogicDevice, _deinterleave_from_device
    class FakeDevice:
        def write(self, endpoint, value, timeout): self.value = bytes(value); return len(value)
    fake = FakeDevice(); instance = object.__new__(ATKLogicDevice); instance.device = fake
    result = instance.signal_start(1, 1_000_000, 25)
    frame = _deinterleave_from_device(fake.value)
    assert frame[9:12] == bytes((0x17, 10, 0x21))
    assert int.from_bytes(frame[12:16], "little") == 200
    assert int.from_bytes(frame[16:20], "little") == 50
    assert result["actual_frequency_hz"] == 1_000_000


def test_model_profiles():
    assert profile_for_level(0).key == "dl16"
    assert profile_for_level(1).key == "dl16p"
    assert PROFILES["dl16"].max_buffer_rate(16) == 250_000_000
    assert PROFILES["dl16p"].max_buffer_rate(8) == 1_000_000_000
    assert PROFILES["dl16p"].max_buffer_rate(16) == 500_000_000


def test_dl16_rejects_plus_only_rate():
    import pytest
    with pytest.raises(ValueError, match="250000000"):
        PROFILES["dl16"].validate_buffer_capture(500_000_000, 8)


def test_all_models_are_detected_from_fpga_identity():
    assert profile_for_identity(0, "DL16", 2) is PROFILES["dl16"]
    assert profile_for_identity(1, "DL16 Plus", 2) is PROFILES["dl16p"]
    assert profile_for_identity(0, "ATK-DL32") is PROFILES["dl32"]
    assert profile_for_identity(0, "ATK_DL32_Plus", 3) is PROFILES["dl32p"]
    assert profile_for_identity(0, "", 3) is PROFILES["dl32"]
    assert profile_for_identity(1, "", 3) is PROFILES["dl32p"]


def test_dl32_profiles_and_trigger_mask():
    assert PROFILES["dl32"].channels == 16
    assert PROFILES["dl32"].max_buffer_rate(12) == 800_000_000
    assert PROFILES["dl32"].max_stream_rate(16) == 125_000_000
    assert PROFILES["dl32p"].channels == 32
    assert PROFILES["dl32p"].max_buffer_rate(12) == 1_000_000_000
    assert PROFILES["dl32p"].max_buffer_rate(15) == 800_000_000
    assert PROFILES["dl32p"].max_buffer_rate(24) == 500_000_000
    assert PROFILES["dl32p"].max_buffer_rate(30) == 400_000_000
    assert PROFILES["dl32p"].max_buffer_rate(32) == 250_000_000
    assert PROFILES["dl32p"].max_stream_rate(32, usb_generation=3) == 50_000_000
    assert PROFILES["dl32p"].max_stream_rate(32, usb_generation=2) == 10_000_000
    config = CaptureConfig([0, 16, 31], 20_000_000, 0.001)
    trigger = _instant_trigger(config, 32)
    assert len(trigger) == 17
    assert trigger[0] == 0xF0
    assert trigger[8] == 0xF0
    assert trigger[15] == 0x0F
    assert trigger[-1] == 1
