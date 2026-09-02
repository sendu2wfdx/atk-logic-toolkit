from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import markdown_report, summarize
from .capture import load_capture
from .decoders import decode_i2c, decode_spi, decode_uart
from .device import scan
from .hardware import CaptureConfig, DL16, parse_channels, parse_duration, parse_rate, save_csv


def _write(value, output: str | None, markdown: bool = False) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        print(output)
    else:
        print(text)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="dl16", description="Analyze ALIENTEK DL16 CSV/VCD captures for MCU firmware work")
    root.add_argument("--version", action="version", version="%(prog)s 0.1.0")
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
    device = sub.add_parser("device"); device.add_argument("action", choices=["scan"]); device.add_argument("--out")
    capture = sub.add_parser("capture", help="capture directly from a DL16 over USB")
    capture.add_argument("out")
    capture.add_argument("--channels", default="D0", help="comma-separated channels, e.g. D0,D1,D7")
    capture.add_argument("--rate", default="20MHz")
    capture.add_argument("--duration", default="10ms")
    capture.add_argument("--threshold", type=float, default=1.6)
    capture.add_argument("--trigger-position", type=float, default=0.5)
    capture.add_argument("--rle", action="store_true")
    capture.add_argument("--timeout", type=float)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "device":
        _write({"devices": scan(), "safety": "read-only descriptor scan; no control commands sent"}, args.out); return 0
    if args.command == "capture":
        config = CaptureConfig(parse_channels(args.channels), parse_rate(args.rate), parse_duration(args.duration), args.threshold, args.trigger_position, args.rle)
        config.validate()
        device = DL16().open()
        try:
            packed = device.capture(config, args.timeout)
        finally:
            device.close()
        count = save_csv(args.out, packed, config)
        _write({"output": args.out, "samples": count, "rate_hz": config.rate_hz, "channels": [f"D{x}" for x in config.channels], "verification": "source-verified; compare first run with ATK-Logic on physical DL16"}, None)
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


if __name__ == "__main__":
    raise SystemExit(main())
