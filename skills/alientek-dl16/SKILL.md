---
name: alientek-dl16
description: Analyze MCU firmware behavior from ALIENTEK/正点原子 logic-analyzer captures, defaulting to the DL16 model. Use for DL16 connection checks, capture-quality planning, ATK-Logic CSV or VCD inspection, UART/I2C/SPI decoding, timing evidence, and correlating bus activity with firmware code. Do not use it to claim unverified live capture or firmware-update support.
---

# ALIENTEK DL16 MCU Analysis

Default to the 16-channel DL16 unless the user names another ALIENTEK model. Use the repository's `dl16` CLI for deterministic parsing and decoding; do not estimate bytes by visually reading screenshots when a capture file is available.

## Workflow

1. Establish the evidence available: ATK-Logic CSV, VCD, wiring/channel map, sample rate, voltage level, trigger condition, firmware binary/source/map, and the behavior under test.
2. Run `dl16 inspect <capture>` before decoding. Flag an inadequate sample rate, missing ground, clipped time window, inactive channel, ambiguous mapping, or likely glitches before drawing protocol conclusions.
3. Generate a baseline with `dl16 analyze <capture> --out <report.md>`.
4. Decode only protocols supported by the observed wiring:
   - `dl16 uart ...` for one asynchronous data line.
   - `dl16 i2c ...` for SCL/SDA.
   - `dl16 spi ...` for CLK plus MOSI and/or MISO, preferably with CS.
5. Correlate decoded frames with firmware evidence by timestamp and experiment. Separate direct observations, likely interpretations, and unverified hypotheses.
6. Preserve the original capture and command parameters next to the report. Never silently change baud, SPI mode, polarity, bit order, or channel mapping just to obtain plausible output.

The tool can directly capture from DL16 with `dl16 capture`. Its implementation follows the official GPL source, but until physical regression is recorded, label it source-verified/hardware-unverified. Do not send reset, bootloader, firmware-update, or undocumented commands through this skill.

## Conditional references

- For DL16 identity, format support, safe wiring, and capture-quality rules, read [references/dl16.md](references/dl16.md).
- For firmware correlation and confidence labels, read [references/firmware-analysis.md](references/firmware-analysis.md) when the task asks what the waveform implies about MCU code or state.

If parsing fails, retain the original file and report the header plus a minimal redacted row. Extend the parser with a regression test instead of destructively converting the only capture.
