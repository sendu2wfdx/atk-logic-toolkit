from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProfile:
    key: str
    display_name: str
    channels: int = 16
    signal_outputs: int = 2
    verified: bool = False

    def max_buffer_rate(self, active_channels: int) -> int:
        if self.key == "dl16-plus":
            return 1_000_000_000 if active_channels <= 8 else 500_000_000
        return 250_000_000

    def max_stream_rate(self, active_channels: int) -> int:
        if active_channels <= 3:
            return 100_000_000
        if active_channels <= 12:
            return 25_000_000
        return 20_000_000

    def validate_buffer_capture(self, rate_hz: int, active_channels: int) -> None:
        maximum = self.max_buffer_rate(active_channels)
        if rate_hz > maximum:
            raise ValueError(
                f"{self.display_name} supports at most {maximum} Hz in buffer mode "
                f"with {active_channels} active channel(s)"
            )


PROFILES = {
    "dl16": DeviceProfile("dl16", "ALIENTEK DL16", verified=True),
    "dl16-plus": DeviceProfile("dl16-plus", "ALIENTEK DL16 Plus"),
    "generic": DeviceProfile("generic", "ALIENTEK Logic Analyzer"),
}


def profile_for_level(level: int | None) -> DeviceProfile:
    if level == 1:
        return PROFILES["dl16-plus"]
    if level == 0:
        return PROFILES["dl16"]
    return PROFILES["generic"]

