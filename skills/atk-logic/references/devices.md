# ATK Logic device reference

## Verified identity and supported paths

- Supported profiles: ALIENTEK/正点原子 DL16, DL16 Plus, DL32, and DL32 Plus.
- Unknown identities are rejected instead of being assigned guessed capabilities.
- USB identity used by the official open-source ATK-Logic application: VID `0x1a86`, PID `0xffcc`.
- Stable input path: CSV exported by ATK-Logic.
- Additional input path: scalar digital VCD.
- `atk-logic device scan` reads USB descriptors only.
- `atk-logic device info` reads the official MCU and FPGA identity responses. It matches the normalized FPGA model name first, then uses level 0/1 only as a USB 2.0 DL16-family fallback.
- `atk-logic capture` implements finite buffer capture using the official endpoint, command framing, configuration fields, 2048-byte lane transform, response packet framing, per-channel data, and optional RLE behavior.

## Profiles

| Profile | Channels | USB | Buffer-mode ceiling | Storage | Bandwidth | Validation |
|---|---:|---:|---|---:|---:|---|
| DL16 | 16 | 2.0 | 250 MHz at 16 channels | 1 Gbit | 50 MHz | Physical device `ATK22` |
| DL16 Plus | 16 | 2.0 | 1 GHz/8ch; 500 MHz/16ch | 3.5 Gbit | 200 MHz | Official material, physical test pending |
| DL32 | 16 | 3.0 | 1 GHz/8ch; 800 MHz/12ch; 500 MHz/16ch | 3.5 Gbit | 200 MHz | Official material, physical test pending |
| DL32 Plus | 32 | 3.0 | 1 GHz/12ch; 800 MHz/15ch; 500 MHz/24ch; 400 MHz/30ch; 250 MHz/32ch | 3.5 Gbit | 200 MHz | Official material, physical test pending |

The DL16 family exposes two signal-generator outputs. Official specifications list four PWM outputs on the DL32 family; this toolkit exposes only the first two until the additional selectors are verified on matching hardware. Only DL32 Plus uses D0–D31 and a 16-byte channel/trigger mask; DL32 itself remains a 16-channel model. This toolkit currently implements finite buffer capture.

The community [Doukeyi-X/ALL-LOGIC](https://github.com/Doukeyi-X/ALL-LOGIC) driver independently implements the shared ATK USB framing and capture packets, but fixes `ATK_MAX_CH` and the reported channel count at 16. It is corroborating protocol evidence, not a DL32 Plus implementation. This toolkit independently extends packet channel IDs and trigger masks through D31; keep DL32-family claims marked hardware-pending until matching devices are tested.

Finite direct capture, completion, stop, multi-channel sampling, and RLE were exercised on physical DL16 serial `ATK22` on 2026-09-02. Signal-generator commands for both outputs were accepted and auto-stop was exercised, but frequency and duty remain protocol-verified rather than electrically measured until a loopback lead or oscilloscope is attached.

## Wiring safety

- Connect analyzer ground to DUT ground before signal leads.
- Confirm the DUT signal range against the physical analyzer's published input limits; do not infer tolerance from a decoded logic level.
- Never attach a logic channel to power, motor, heater, mains, or other analog/high-energy nodes.
- Keep leads short at high clock rates and include the channel-to-signal map in the report.

## Capture quality

- UART: use at least 8 samples/bit; 10–20 is preferable. Capture enough idle time before the first start bit.
- I²C: capture both SCL and SDA. Preserve repeated START conditions and ACK/NACK bits.
- SPI: record CLK and CS plus each data direction needed. State mode, bit order, word width, and CS polarity.
- PWM/timing: include multiple periods and report jitter distribution rather than a single interval.
- Sparse edge exports are suitable for protocol timing but not for claiming a uniform hardware sample rate.

## Tool limits

CSV dialect and time units are auto-detected. Unknown/tri-state VCD values are conservatively mapped low. Vector VCD signals and analog traces are not supported. Protocol decoders cover ordinary UART, 7-bit I²C framing, and SPI modes 0–3; they do not replace electrical-integrity analysis.
