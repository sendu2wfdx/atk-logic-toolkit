from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Capture:
    times: list[float]
    channels: dict[str, list[int]]
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.times:
            raise ValueError("capture has no samples")
        if any(b < a for a, b in zip(self.times, self.times[1:])):
            raise ValueError("timestamps are not monotonic")
        for name, values in self.channels.items():
            if len(values) != len(self.times):
                raise ValueError(f"channel {name!r} length does not match timestamps")
            if any(value not in (0, 1) for value in values):
                raise ValueError(f"channel {name!r} contains a non-digital value")

    @property
    def duration(self) -> float:
        return self.times[-1] - self.times[0] if len(self.times) > 1 else 0.0


_TIME_FACTORS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9}


def _time_factor(label: str) -> float:
    text = label.strip().lower().replace("μ", "µ")
    match = re.search(r"(?:\[|\(|\b)(ns|us|µs|ms|s)(?:\]|\)|\b)", text)
    return _TIME_FACTORS.get(match.group(1), 1.0) if match else 1.0


def load_capture(path: str | Path) -> Capture:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".vcd":
        return load_vcd(source)
    if suffix in {".csv", ".txt", ".tsv"}:
        return load_csv(source)
    raise ValueError(f"unsupported capture format: {suffix or '<none>'}; use CSV/TSV or VCD")


def load_csv(path: str | Path) -> Capture:
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    metadata: dict[str, str] = {"source": str(source), "format": "csv"}
    data_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(";") or stripped.startswith("#"):
            item = stripped[1:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                metadata[key.strip().lower().replace(" ", "_")] = value.strip()
            continue
        if stripped:
            data_lines.append(line)
    if not data_lines:
        raise ValueError("CSV contains no table")
    sample = "\n".join(data_lines[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = list(csv.reader(data_lines, delimiter=delimiter))
    header = [cell.strip() for cell in rows[0]]
    time_index = next((i for i, name in enumerate(header) if re.search(r"time|timestamp|时间", name, re.I)), 0)
    factor = _time_factor(header[time_index])
    channel_indices = [i for i in range(len(header)) if i != time_index]
    channels = {header[i] or f"D{i}": [] for i in channel_indices}
    times: list[float] = []
    for line_number, row in enumerate(rows[1:], 2):
        if len(row) < len(header):
            continue
        try:
            timestamp = float(row[time_index].strip()) * factor
            values = []
            for i in channel_indices:
                raw = row[i].strip().lower()
                values.append(1 if raw in {"1", "h", "high", "true"} else 0 if raw in {"0", "l", "low", "false"} else int(raw, 0))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid digital row at line {line_number}: {exc}") from exc
        times.append(timestamp)
        for (name, target), value in zip(channels.items(), values):
            target.append(value)
    capture = Capture(times, channels, metadata)
    capture.validate()
    return capture


def load_vcd(path: str | Path) -> Capture:
    source = Path(path)
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    scale = 1e-9
    symbols: dict[str, str] = {}
    state: dict[str, int] = {}
    snapshots: list[tuple[float, dict[str, int]]] = []
    current_time = 0.0
    for line in lines:
        text = line.strip()
        if text.startswith("$timescale"):
            match = re.search(r"([0-9.]+)\s*(s|ms|us|µs|ns|ps)", text, re.I)
            if match:
                scale = float(match.group(1)) * {**_TIME_FACTORS, "ps": 1e-12}[match.group(2).lower()]
        elif text.startswith("$var"):
            parts = text.split()
            if len(parts) >= 5 and parts[2] == "1":
                symbols[parts[3]] = parts[4]
                state[parts[3]] = 0
        elif text.startswith("#"):
            if state:
                snapshots.append((current_time, dict(state)))
            current_time = float(text[1:]) * scale
        elif len(text) >= 2 and text[0] in "01xXzZ" and text[1:] in symbols:
            state[text[1:]] = 1 if text[0] == "1" else 0
    if state:
        snapshots.append((current_time, dict(state)))
    times = [item[0] for item in snapshots]
    channels = {name: [values[symbol] for _, values in snapshots] for symbol, name in symbols.items()}
    capture = Capture(times, channels, {"source": str(source), "format": "vcd", "timescale_s": str(scale)})
    capture.validate()
    return capture

