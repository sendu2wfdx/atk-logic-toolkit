from __future__ import annotations

from dataclasses import dataclass


def _rate_for(active_channels: int, limits: tuple[tuple[int, int], ...]) -> int:
    if active_channels < 1:
        raise ValueError("active channel count must be positive")
    for maximum_channels, rate_hz in limits:
        if active_channels <= maximum_channels:
            return rate_hz
    return 0


@dataclass(frozen=True)
class DeviceProfile:
    key: str
    display_name: str
    channels: int
    usb_generation: int
    hardware_storage_bits: int
    measurement_bandwidth_hz: int
    buffer_limits: tuple[tuple[int, int], ...]
    stream_usb3_limits: tuple[tuple[int, int], ...]
    stream_usb2_limits: tuple[tuple[int, int], ...]
    signal_outputs: int
    verified: bool = False

    def max_buffer_rate(self, active_channels: int) -> int:
        return _rate_for(active_channels, self.buffer_limits)

    def max_stream_rate(self, active_channels: int, usb_generation: int | None = None) -> int:
        generation = self.usb_generation if usb_generation is None else usb_generation
        return _rate_for(active_channels, self.stream_usb3_limits if generation >= 3 else self.stream_usb2_limits)

    def validate_buffer_capture(self, rate_hz: int, active_channels: int) -> None:
        if not 1 <= active_channels <= self.channels:
            raise ValueError(f"{self.display_name} supports 1..{self.channels} active channels")
        maximum = self.max_buffer_rate(active_channels)
        if rate_hz > maximum:
            raise ValueError(
                f"{self.display_name} supports at most {maximum} Hz in buffer mode "
                f"with {active_channels} active channel(s)"
            )


USB2_STREAM = ((3, 100_000_000), (6, 50_000_000), (16, 20_000_000))
DL32_STREAM_USB3 = ((3, 1_000_000_000), (6, 500_000_000), (12, 250_000_000), (16, 125_000_000))
DL32P_STREAM_USB3 = DL32_STREAM_USB3 + ((30, 100_000_000), (32, 50_000_000))
DL32P_STREAM_USB2 = USB2_STREAM + ((32, 10_000_000),)

PROFILES = {
    "dl16": DeviceProfile("dl16", "ALIENTEK DL16", 16, 2, 1_000_000_000, 50_000_000,
                          ((16, 250_000_000),), USB2_STREAM, USB2_STREAM, 2, True),
    "dl16p": DeviceProfile("dl16p", "ALIENTEK DL16 Plus", 16, 2, 3_500_000_000, 200_000_000,
                           ((8, 1_000_000_000), (16, 500_000_000)), USB2_STREAM, USB2_STREAM, 2),
    "dl32": DeviceProfile("dl32", "ALIENTEK DL32", 16, 3, 3_500_000_000, 200_000_000,
                          ((8, 1_000_000_000), (12, 800_000_000), (16, 500_000_000)),
                          DL32_STREAM_USB3, USB2_STREAM, 4),
    "dl32p": DeviceProfile("dl32p", "ALIENTEK DL32 Plus", 32, 3, 3_500_000_000, 200_000_000,
                           ((12, 1_000_000_000), (15, 800_000_000), (24, 500_000_000),
                            (30, 400_000_000), (32, 250_000_000)),
                           DL32P_STREAM_USB3, DL32P_STREAM_USB2, 4),
}


def _normalized_name(fpga_name: str) -> str:
    return "".join(character for character in fpga_name.upper() if character.isalnum())


def profile_for_identity(level: int | None, fpga_name: str = "", usb_generation: int | None = None) -> DeviceProfile | None:
    """Map the identity fields returned by the official MCU/FPGA queries."""
    name = _normalized_name(fpga_name)
    if "DL32PLUS" in name or "DL32P" in name:
        return PROFILES["dl32p"]
    if "DL32" in name:
        return PROFILES["dl32"]
    if "DL16PLUS" in name or "DL16P" in name:
        return PROFILES["dl16p"]
    if "DL16" in name:
        return PROFILES["dl16p" if level == 1 else "dl16"]
    if usb_generation == 3:
        if level == 1:
            return PROFILES["dl32p"]
        if level == 0:
            return PROFILES["dl32"]
    if usb_generation in (None, 2):
        if level == 1:
            return PROFILES["dl16p"]
        if level == 0:
            return PROFILES["dl16"]
    return None


def profile_for_level(level: int | None) -> DeviceProfile | None:
    return profile_for_identity(level)
