---
name: atk-logic
description: Capture and analyze MCU firmware behavior with ALIENTEK/正点原子 logic analyzers, automatically selecting a supported device profile and defaulting conservatively to DL16. Use for device checks, capture planning, ATK-Logic CSV or VCD inspection, UART/I2C/SPI decoding, timing evidence, signal generation, and correlating bus activity with firmware code. Do not use it for firmware updates or undocumented device commands.
---

# ATK Logic MCU Analysis

Use `atk-logic device info` to identify the connected model. Default conservatively to the 16-channel DL16 profile when the user names no model and automatic identification is unavailable. Use the repository's `atk-logic` CLI for deterministic parsing and decoding; `dl16` is only a compatibility alias.

## Workflow

1. Establish the evidence available: ATK-Logic CSV, VCD, wiring/channel map, sample rate, voltage level, trigger condition, firmware binary/source/map, and the behavior under test.
2. Run `atk-logic inspect <capture>` before decoding. Flag an inadequate sample rate, missing ground, clipped time window, inactive channel, ambiguous mapping, or likely glitches before drawing protocol conclusions.
3. Generate a baseline with `atk-logic analyze <capture> --out <report.md>`.
4. Decode only protocols supported by the observed wiring:
   - `atk-logic uart ...` for one asynchronous data line.
   - `atk-logic i2c ...` for SCL/SDA.
   - `atk-logic spi ...` for CLK plus MOSI and/or MISO, preferably with CS.
5. Correlate decoded frames with firmware evidence by timestamp and experiment. Separate direct observations, likely interpretations, and unverified hypotheses.
6. Preserve the original capture and command parameters next to the report. Never silently change baud, SPI mode, polarity, bit order, or channel mapping just to obtain plausible output.

Use `atk-logic signal start` and `atk-logic signal stop` for the two onboard signal-generator outputs. Prefer `--duration` during tests so an output is automatically stopped. Do not infer output correctness from floating inputs; request an explicit loopback wire to a named D0–D15 channel before measuring frequency or duty.

The tool can directly capture from supported devices with `atk-logic capture`. Ordinary and RLE finite captures have been verified on physical DL16 serial `ATK22`. DL16 Plus and 32-channel DL32 Pro have separate channel/rate profiles and await corresponding physical regression. Do not send reset, bootloader, firmware-update, or undocumented commands through this skill.

## Conditional references

- For device profiles, format support, safe wiring, and capture-quality rules, read [references/devices.md](references/devices.md).
- For firmware correlation and confidence labels, read [references/firmware-analysis.md](references/firmware-analysis.md) when the task asks what the waveform implies about MCU code or state.

If parsing fails, retain the original file and report the header plus a minimal redacted row. Extend the parser with a regression test instead of destructively converting the only capture.
