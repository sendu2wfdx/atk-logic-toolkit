from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import markdown_report, summarize
from .capture import load_capture
from .decoders import decode_i2c, decode_spi, decode_uart
from .device import scan
from .hardware import ATKLogicDevice, CaptureConfig, parse_channels, parse_duration, parse_rate, save_csv
from .profiles import PROFILES


def _write(value, output: str | None, markdown: bool = False) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        print(output)
    else:
        print(text)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="atk-logic", description="Capture and analyze ALIENTEK logic-analyzer waveforms for MCU firmware work")
    root.add_argument("--version", action="version", version="%(prog)s 0.4.0")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("inspect", "analyze"):
        item = sub.add_parser(name)
        item.add_argument("capture")
        item.add_argument("--out")
    uart = sub.add_parser("uart")
    uart.add_argument("capture"); uart.add_argument("--channel", default="D0"); uart.add_argument("--baud", type=float, required=True)
    uart.add_argument("--data-bits", type=int, default=8); uart.add_argument("--parity", choices=["none", "even", "odd"], default="none")
    uart.add_argument("--stop-bits", type=float, default=1); uart.add_argument("--inverted", action="store_true"); uart.add_argument("--out")
    i2c = sub.add_parser("i2c")
    i2c.add_argument("capture"); i2c.add_argument("--scl", required=True); i2c.add_argument("--sda", required=True); i2c.add_argument("--out")
    spi = sub.add_parser("spi")
    spi.add_argument("capture"); spi.add_argument("--clk", required=True); spi.add_argument("--mosi"); spi.add_argument("--miso"); spi.add_argument("--cs")
    spi.add_argument("--mode", type=int, choices=range(4), default=0); spi.add_argument("--lsb-first", action="store_true"); spi.add_argument("--cs-active", type=int, choices=(0, 1), default=0); spi.add_argument("--word-bits", type=int, default=8); spi.add_argument("--out")
    device = sub.add_parser("device"); device.add_argument("action", choices=["scan", "info"]); device.add_argument("--out")
    capture = sub.add_parser("capture", help="capture directly from a DL16 over USB")
    capture.add_argument("out")
    capture.add_argument("--channels", default="D0", help="comma-separated channels, e.g. D0,D1,D7")
    capture.add_argument("--rate", default="20MHz")
    capture.add_argument("--duration", default="10ms")
    capture.add_argument("--threshold", type=float, default=1.6)
    capture.add_argument("--trigger-position", type=float, default=0.5)
    capture.add_argument("--rle", action="store_true")
    capture.add_argument("--timeout", type=float)
    capture.add_argument("--model", choices=("auto", *PROFILES), default="auto")
    signal = sub.add_parser("signal", help="control the two DL16 signal-generator outputs")
    signal_sub = signal.add_subparsers(dest="signal_action", required=True)
    signal_start = signal_sub.add_parser("start")
    signal_start.add_argument("--channel", type=int, choices=(0, 1), required=True)
    signal_start.add_argument("--frequency", required=True, help="1Hz..20MHz")
    signal_start.add_argument("--duty", type=int, default=50)
    signal_start.add_argument("--duration", help="optional auto-stop duration, e.g. 2s")
    signal_stop = signal_sub.add_parser("stop")
    signal_stop.add_argument("--channel", choices=("0", "1", "all"), default="all")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "device":
        if args.action == "scan":
            _write({"devices": scan(), "safety": "read-only descriptor scan; no control commands sent"}, args.out)
        else:
            device = ATKLogicDevice().open()
            try:
                _write(device.read_device_info(), args.out)
            finally:
                device.close()
        return 0
    if args.command == "capture":
        config = CaptureConfig(parse_channels(args.channels), parse_rate(args.rate), parse_duration(args.duration), args.threshold, args.trigger_position, args.rle)
        config.validate()
        device = ATKLogicDevice().open()
        try:
            profile = device.resolve_profile(args.model)
            packed = device.capture(config, args.timeout, profile)
        finally:
            device.close()
        count = save_csv(args.out, packed, config)
        _write({"output": args.out, "model": profile.display_name, "profile": profile.key, "samples": count, "rate_hz": config.rate_hz, "channels": [f"D{x}" for x in config.channels]}, None)
        return 0
    if args.command == "signal":
        device = ATKLogicDevice().open()
        try:
            if args.signal_action == "start":
                result = device.signal_start(args.channel, parse_rate(args.frequency), args.duty)
                if args.duration:
                    import time
                    duration = parse_duration(args.duration)
                    if duration <= 0:
                        raise ValueError("duration must be positive")
                    time.sleep(duration)
                    device.signal_stop(args.channel)
                    result["auto_stopped_after_s"] = duration
                _write(result, None)
            else:
                channel = None if args.channel == "all" else int(args.channel)
                device.signal_stop(channel)
                _write({"stopped": "all" if channel is None else channel}, None)
        finally:
            device.close()
        return 0
    capture = load_capture(args.capture)
    if args.command == "inspect":
        _write(summarize(capture), args.out)
    elif args.command == "analyze":
        _write(markdown_report(capture, args.capture), args.out, markdown=True)
    elif args.command == "uart":
        _write({"protocol": "uart", "channel": args.channel, "baud": args.baud, "frames": decode_uart(capture, args.channel, args.baud, args.data_bits, args.parity, args.stop_bits, args.inverted)}, args.out)
    elif args.command == "i2c":
        _write({"protocol": "i2c", "scl": args.scl, "sda": args.sda, "events": decode_i2c(capture, args.scl, args.sda)}, args.out)
    elif args.command == "spi":
        if not args.mosi and not args.miso:
            raise SystemExit("SPI requires --mosi and/or --miso")
        _write({"protocol": "spi", "mode": args.mode, "transactions": decode_spi(capture, args.clk, args.mosi, args.miso, args.cs, args.mode, args.lsb_first, args.cs_active, args.word_bits)}, args.out)
    return 0


def entrypoint() -> int:
    try:
        return main()
    except (RuntimeError, TimeoutError, ValueError, KeyError, OSError) as exc:
        message = str(exc)
        if "Access denied" in message or "insufficient permissions" in message:
            message = "ATK Logic device is busy or access is denied; close ALL LOGIC/ATK-Logic and retry"
        print(f"atk-logic: error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(entrypoint())
