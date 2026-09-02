from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass

from .capture import Capture


@dataclass
class ChannelStats:
    channel: str
    edges: int
    rising_edges: int
    falling_edges: int
    high_fraction: float
    mean_period_s: float | None
    frequency_hz: float | None
    shortest_pulse_s: float | None
    glitch_candidates: int


def edge_indices(values: list[int], rising: bool | None = None) -> list[int]:
    result = []
    for i in range(1, len(values)):
        if values[i] == values[i - 1]:
            continue
        if rising is None or (rising and values[i] == 1) or (rising is False and values[i] == 0):
            result.append(i)
    return result


def summarize(capture: Capture) -> dict:
    deltas = [b - a for a, b in zip(capture.times, capture.times[1:]) if b > a]
    nominal_dt = statistics.median(deltas) if deltas else None
    channel_stats: list[dict] = []
    for name, values in capture.channels.items():
        rising = edge_indices(values, True)
        falling = edge_indices(values, False)
        edges = sorted(rising + falling)
        rising_times = [capture.times[i] for i in rising]
        periods = [b - a for a, b in zip(rising_times, rising_times[1:]) if b > a]
        mean_period = statistics.median(periods) if periods else None
        pulse_widths = [capture.times[b] - capture.times[a] for a, b in zip(edges, edges[1:]) if b > a]
        shortest = min(pulse_widths) if pulse_widths else None
        glitch_limit = nominal_dt * 2.5 if nominal_dt else 0.0
        stats = ChannelStats(
            name, len(edges), len(rising), len(falling), sum(values) / len(values), mean_period,
            1.0 / mean_period if mean_period else None, shortest,
            sum(width < glitch_limit for width in pulse_widths) if glitch_limit else 0,
        )
        channel_stats.append(asdict(stats))
    return {
        "metadata": capture.metadata,
        "samples": len(capture.times),
        "duration_s": capture.duration,
        "nominal_sample_interval_s": nominal_dt,
        "estimated_sample_rate_hz": 1.0 / nominal_dt if nominal_dt else None,
        "channels": channel_stats,
    }


def markdown_report(capture: Capture, source_name: str) -> str:
    result = summarize(capture)
    rate = result["estimated_sample_rate_hz"]
    lines = [
        "# DL16 MCU 波形分析报告", "", "## 捕获概况", "",
        f"- 来源：`{source_name}`", f"- 样本数：{result['samples']}",
        f"- 捕获时长：{result['duration_s']:.9g} s",
        f"- 估算采样率：{rate:.9g} Hz" if rate else "- 估算采样率：稀疏边沿数据，无法可靠估算",
        "", "## 通道观测", "",
        "| 通道 | 边沿 | 上升 | 下降 | 高电平占比 | 估算频率 | 最短脉宽 | 毛刺候选 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["channels"]:
        freq = f"{item['frequency_hz']:.6g} Hz" if item["frequency_hz"] else "—"
        pulse = f"{item['shortest_pulse_s']:.6g} s" if item["shortest_pulse_s"] else "—"
        lines.append(f"| {item['channel']} | {item['edges']} | {item['rising_edges']} | {item['falling_edges']} | {item['high_fraction']:.2%} | {freq} | {pulse} | {item['glitch_candidates']} |")
    lines += [
        "", "## 结论边界", "",
        "本节统计是由波形直接得到的观测事实。协议含义、命令语义和固件状态机属于解释，必须结合解码字节、接线定义、固件符号或重复实验另行证明。",
        "", "## 后续分析", "",
        "1. 对活动通道按 UART、I²C 或 SPI 接线关系执行解码。",
        "2. 将关键帧与固件函数、寄存器访问或状态切换按时间对齐。",
        "3. 对无法解释的帧重复采集，并一次只改变一个输入条件。",
    ]
    return "\n".join(lines) + "\n"

