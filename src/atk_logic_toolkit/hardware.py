from __future__ import annotations

import csv
import math
import struct
import time
from dataclasses import dataclass
from pathlib import Path

from .device import ATK_LOGIC_PRODUCT_ID, ATK_LOGIC_VENDOR_ID, usb_backend
from .profiles import PROFILES, DeviceProfile, profile_for_level

OUT_ENDPOINT = 0x02
IN_ENDPOINT = 0x81
BLOCK = 2048
RATES = [1_000_000, 2_000_000, 4_000_000, 5_000_000, 10_000_000, 20_000_000,
         25_000_000, 40_000_000, 50_000_000, 100_000_000, 200_000_000,
         250_000_000, 500_000_000, 1_000_000_000]


@dataclass
class CaptureConfig:
    channels: list[int]
    rate_hz: int
    duration_s: float
    threshold_v: float = 1.6
    trigger_position: float = 0.5
    rle: bool = False

    @property
    def depth(self) -> int:
        return max(1, round(self.rate_hz * self.duration_s))

    def validate(self) -> None:
        if not self.channels or any(ch not in range(16) for ch in self.channels):
            raise ValueError("channels must contain one or more values from D0 to D15")
        if self.rate_hz not in RATES:
            raise ValueError(f"unsupported rate; choose one of: {', '.join(str(x) for x in RATES)}")
        if not 0.0 <= self.trigger_position <= 1.0:
            raise ValueError("trigger position must be between 0 and 1")
        if not -5.0 <= self.threshold_v <= 5.0:
            raise ValueError("threshold must be between -5.0 V and 5.0 V")
        if self.duration_s <= 0:
            raise ValueError("duration must be positive")


def _crc32_atk(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
    return crc ^ 0xFFFFFFFF


def _u40(value: int) -> bytes:
    return value.to_bytes(5, "little")


def _interleave_for_device(data: bytes) -> bytes:
    padded = data + bytes((-len(data)) % BLOCK)
    output = bytearray(len(padded))
    for base in range(0, len(padded), BLOCK):
        words = struct.unpack_from("<1024H", padded, base)
        for j in range(256):
            for lane in range(4):
                struct.pack_into("<H", output, base + lane * 512 + j * 2, words[j * 4 + lane])
    return bytes(output)


def _deinterleave_from_device(data: bytes) -> bytes:
    usable = len(data) // BLOCK * BLOCK
    output = bytearray(usable)
    for base in range(0, usable, BLOCK):
        for j in range(256):
            for lane in range(4):
                word = struct.unpack_from("<H", data, base + lane * 512 + j * 2)[0]
                struct.pack_into("<H", output, base + (j * 4 + lane) * 2, word)
    return bytes(output)


def _command(code: int, payload: bytes = b"") -> bytes:
    body = bytes((code, len(payload) + 1)) + payload
    framed = bytes(8) + b"\x0a" + body + b"\x0b" + struct.pack("<I", _crc32_atk(body))
    return _interleave_for_device(framed)


def _configuration(config: CaptureConfig) -> bytes:
    flags = 0x80 | (0x40 if config.rle else 0)
    threshold = round(abs(config.threshold_v) * 10) | (0x80 if config.threshold_v < 0 else 0)
    rate_index = RATES.index(config.rate_hz) + 1
    trigger_depth = round(config.depth * config.trigger_position)
    return bytes((flags, threshold, rate_index)) + _u40(config.depth) + _u40(trigger_depth)


def _instant_trigger(config: CaptureConfig) -> bytes:
    pairs = bytearray(8)
    for ch in config.channels:
        pairs[ch // 2] |= 0xF0 if ch % 2 == 0 else 0x0F
    return bytes(pairs) + b"\x01"


def _packets(buffer: bytearray):
    cursor = 0
    while cursor + 6 <= len(buffer):
        if buffer[cursor] != 0x0A or not 1 <= buffer[cursor + 1] <= 6:
            cursor += 1
            continue
        length = int.from_bytes(buffer[cursor + 2:cursor + 4], "little")
        end = cursor + 4 + length
        if end + 1 >= len(buffer):
            break
        if buffer[end:end + 2] != b"\x00\x0b":
            cursor += 1
            continue
        yield buffer[cursor + 1], bytes(buffer[cursor + 4:end])
        cursor = end + 2
    if cursor:
        del buffer[:cursor]


class ATKLogicDevice:
    def __init__(self, device=None):
        try:
            import usb.core
        except ImportError as exc:
            raise RuntimeError("DL16 capture requires PyUSB; install with pip install -e '.[usb]'") from exc
        self.device = device or usb.core.find(idVendor=ATK_LOGIC_VENDOR_ID, idProduct=ATK_LOGIC_PRODUCT_ID, backend=usb_backend())
        if self.device is None:
            raise RuntimeError("ATK Logic analyzer not found (expected USB 1a86:ffcc)")
        self.last_capture_stats: dict = {}
        self.device_info: dict = {}

    def open(self):
        try:
            self.device.set_configuration()
        except Exception:
            pass
        try:
            import usb.util
            if self.device.is_kernel_driver_active(0):
                self.device.detach_kernel_driver(0)
            usb.util.claim_interface(self.device, 0)
        except (NotImplementedError, AttributeError):
            pass
        return self

    def close(self):
        try:
            import usb.util
            usb.util.release_interface(self.device, 0)
        except Exception:
            pass

    def send(self, code: int, payload: bytes = b"") -> None:
        written = self.device.write(OUT_ENDPOINT, _command(code, payload), timeout=1000)
        if written != BLOCK:
            raise RuntimeError(f"short USB write: {written}/{BLOCK}")

    def signal_start(self, channel: int, frequency_hz: int, duty_percent: int) -> dict:
        if channel not in (0, 1):
            raise ValueError("signal channel must be 0 or 1")
        if not 1 <= frequency_hz <= 20_000_000:
            raise ValueError("signal frequency must be between 1 Hz and 20 MHz")
        if not 1 <= duty_percent <= 99:
            raise ValueError("duty must be between 1 and 99 percent")
        period_ticks = round(200_000_000 / frequency_hz)
        high_ticks = round(period_ticks * duty_percent / 100)
        selector = 0x21 if channel else 0x11
        payload = bytes((selector,)) + struct.pack("<II", period_ticks, high_ticks)
        self.send(0x17, payload)
        return {"channel": channel, "requested_frequency_hz": frequency_hz,
                "actual_frequency_hz": 200_000_000 / period_ticks,
                "requested_duty_percent": duty_percent,
                "actual_duty_percent": high_ticks / period_ticks * 100,
                "period_ticks": period_ticks, "high_ticks": high_ticks}

    def signal_stop(self, channel: int | None = None) -> None:
        channels = (0, 1) if channel is None else (channel,)
        if any(item not in (0, 1) for item in channels):
            raise ValueError("signal channel must be 0, 1, or all")
        for item in channels:
            self.send(0x17, bytes((0x20 if item else 0x10,)))

    def read_device_info(self) -> dict:
        """Read the official MCU identity response and map its model level."""
        self.drain()
        self.send_mcu(0x81)
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            try:
                response = bytes(self.device.read(IN_ENDPOINT, 512, timeout=200))
            except Exception as exc:
                if "timed out" in str(exc).lower() or getattr(exc, "errno", None) in (60, 110):
                    continue
                raise
            marker = response.find(b"\x0a\x81\x01")
            if marker >= 0 and len(response) >= marker + 9:
                data = response[marker:]
                level = data[8]
                profile = profile_for_level(level)
                self.device_info = {
                    "profile": profile.key,
                    "model": profile.display_name,
                    "mcu_version": data[4] * 10 + data[5],
                    "hardware_version": data[6],
                    "level": level,
                    "boot_state": data[3],
                }
                return self.device_info
        self.device_info = {"profile": "generic", "model": PROFILES["generic"].display_name,
                            "warning": "MCU identity response not received"}
        return self.device_info

    def resolve_profile(self, requested: str = "auto") -> DeviceProfile:
        if requested != "auto":
            return PROFILES[requested]
        info = self.read_device_info()
        return PROFILES[info["profile"]]

    def send_mcu(self, code: int, payload: bytes = b"") -> None:
        """Send one of the official fixed-size MCU control messages."""
        message = b"\x0a" + bytes((code,)) + payload
        message += bytes(512 - len(message))
        written = self.device.write(OUT_ENDPOINT, message, timeout=1000)
        if written != 512:
            raise RuntimeError(f"short MCU USB write: {written}/512")

    def drain(self, max_bytes: int = 64 * 1024 * 1024) -> int:
        """Discard endpoint data until an idle timeout, as the official client does."""
        count = 0
        total = 0
        while total < max_bytes:
            try:
                data = self.device.read(IN_ENDPOINT, 16384, timeout=50)
                count += 1
                total += len(data)
            except Exception as exc:
                if "timed out" in str(exc).lower() or getattr(exc, "errno", None) in (60, 110):
                    break
                raise
        if total >= max_bytes:
            raise RuntimeError(f"ATK Logic endpoint did not become idle while draining {total} bytes")
        return count

    def capture(self, config: CaptureConfig, timeout_s: float | None = None,
                profile: DeviceProfile | None = None) -> dict[int, bytes]:
        config.validate()
        profile = profile or self.resolve_profile()
        profile.validate_buffer_capture(config.rate_hz, len(config.channels))
        self.send_mcu(0x87, b"\x01")
        try:
            self.device.read(IN_ENDPOINT, 512, timeout=100)
        except Exception:
            pass
        self.drain()
        self.send(0x11, _configuration(config))
        time.sleep(0.03)
        self.send(0x12, _instant_trigger(config))
        raw = bytearray()
        channel_data = {channel: bytearray() for channel in config.channels}
        deadline = time.monotonic() + (timeout_s or max(5.0, config.duration_s * 4 + 2))
        complete = False
        expected_bytes = math.ceil(config.depth / 8)
        bytes_received = 0
        packet_counts: dict[int, int] = {}
        replies: list[str] = []
        try:
            while time.monotonic() < deadline and not all(len(data) >= expected_bytes for data in channel_data.values()):
                try:
                    chunk = bytes(self.device.read(IN_ENDPOINT, 16384, timeout=250))
                except Exception as exc:
                    if "timed out" in str(exc).lower() or getattr(exc, "errno", None) in (60, 110):
                        continue
                    raise
                raw.extend(_deinterleave_from_device(chunk))
                bytes_received += len(chunk)
                for order, payload in _packets(raw):
                    packet_counts[order] = packet_counts.get(order, 0) + 1
                    if order == 1 and len(payload) >= 2:
                        channel = payload[0]
                        if channel in channel_data:
                            data = payload[2:]
                            if config.rle:
                                expanded = bytearray()
                                for i in range(0, len(data) - 1, 2):
                                    expanded.extend(bytes((data[i + 1],)) * data[i])
                                data = bytes(expanded)
                            channel_data[channel].extend(data)
                    elif order == 6:
                        complete = True
                    elif order == 4:
                        replies.append(payload.hex())
        finally:
            try:
                self.send(0x15)
            except Exception:
                pass
        self.last_capture_stats = {"profile": profile.key, "bytes_received": bytes_received, "packets": packet_counts, "replies": replies, "channel_bytes": {f"D{k}": len(v) for k, v in channel_data.items()}}
        enough_data = all(len(data) >= expected_bytes for data in channel_data.values())
        if not enough_data:
            raise TimeoutError(f"ATK Logic capture incomplete: expected={expected_bytes} bytes/channel, complete_packet={complete}, stats={self.last_capture_stats}, buffered={len(raw)} bytes")
        if not any(channel_data.values()):
            raise RuntimeError(f"ATK Logic device completed without sample data: {self.last_capture_stats}")
        return {channel: bytes(data) for channel, data in channel_data.items()}


# Backward-compatible alias from versions 0.1/0.2.
DL16 = ATKLogicDevice


def save_csv(path: str | Path, packed: dict[int, bytes], config: CaptureConfig) -> int:
    available = min((len(data) * 8 for data in packed.values()), default=0)
    count = min(config.depth, available)
    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Time[s]"] + [f"D{channel}" for channel in config.channels])
        for sample in range(count):
            row = [f"{sample / config.rate_hz:.12g}"]
            for channel in config.channels:
                row.append((packed[channel][sample // 8] >> (sample % 8)) & 1)
            writer.writerow(row)
    return count


def parse_rate(value: str) -> int:
    text = value.strip().lower().replace(" ", "")
    factors = {"ghz": 1_000_000_000, "mhz": 1_000_000, "khz": 1_000, "hz": 1}
    for suffix, factor in factors.items():
        if text.endswith(suffix):
            return round(float(text[:-len(suffix)]) * factor)
    return int(text)


def parse_duration(value: str) -> float:
    text = value.strip().lower().replace(" ", "")
    factors = {"ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9, "s": 1}
    for suffix, factor in factors.items():
        if text.endswith(suffix):
            return float(text[:-len(suffix)]) * factor
    return float(text)


def parse_channels(value: str) -> list[int]:
    result = []
    for item in value.split(","):
        text = item.strip().upper()
        if text.startswith("D"):
            text = text[1:]
        result.append(int(text))
    return sorted(set(result))
