# ATK Logic device reference

## Verified identity and supported paths

- Supported profiles: ALIENTEK/正点原子 DL16, DL16 Plus, and a conservative generic ATK Logic fallback.
- Default fallback: DL16, 16 digital channels.
- USB identity used by the official open-source ATK-Logic application: VID `0x1a86`, PID `0xffcc`.
- Stable input path: CSV exported by ATK-Logic.
- Additional input path: scalar digital VCD.
- `atk-logic device scan` reads USB descriptors only.
- `atk-logic device info` reads the official MCU identity response and maps device level 0 to DL16 and level 1 to DL16 Plus.
- `atk-logic capture` implements finite buffer capture using the official endpoint, command framing, configuration fields, 2048-byte lane transform, response packet framing, per-channel data, and optional RLE behavior.

## Profiles

| Profile | Channels | Buffer-mode ceiling | Validation |
|---|---:|---|---|
| DL16 | 16 | 250 MHz | Physical device `ATK22` |
| DL16 Plus | 16 | 1 GHz at up to 8 channels; 500 MHz at 9–16 channels | Official source/UI, physical test pending |
| Generic | 16 | Conservative 250 MHz | Compatibility fallback |

Both named models expose two signal-generator outputs in the official client. Stream ceilings are 100 MHz for up to 3 channels, 25 MHz for 4–12, and 20 MHz for 13–16. This toolkit currently implements finite buffer capture.

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
