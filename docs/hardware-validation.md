# ATK Logic hardware validation: DL16

Date: 2026-09-03
Host: Windows
Device: ALIENTEK DL16, VID:PID `1a86:ffcc`, manufacturer `ATK`, product
`ATK-Logic-Analyzer`, USB serial `ATK22`

## Passed

| Test | Result |
|---|---|
| USB enumeration through bundled libusb backend | Device and descriptors found |
| Automatic device profile | Level 0 and FPGA name `DL16` mapped to DL16; MCU 19, hardware revision 2, FPGA 222 |
| Auto-profile D0/D1 capture, 1 MHz, 1 ms | DL16 selected; exactly 1,000 samples/channel |
| FPGA wake and endpoint drain | Repeated captures start from a clean boundary |
| D0, 1 MHz, 1 ms, ordinary mode | Exactly 1,000 samples |
| D0/D1, 1 MHz, 1 ms, ordinary mode | Exactly 1,000 samples/channel |
| D0–D15, 20 MHz, 1 ms, ordinary mode | Exactly 20,000 samples/channel |
| D0/D1, 1 MHz, 2 ms, RLE mode | Exactly 2,000 samples/channel after expansion |
| Signal OUT0, 1 kHz, 50%, 0.5 s | Command accepted; automatic stop succeeded |
| Signal OUT1, 2 kHz, 25%, 0.5 s | Command accepted; automatic stop succeeded |
| Stop all signal outputs | Command accepted |
| PWM0 → D0 loopback, requested 100 kHz / 25% | Measured 100 kHz / 25%; 200 rising and 200 falling edges in 2 ms; no glitch candidates |
| PWM1 → D1 loopback, requested 250 kHz / 60% | Measured 250 kHz / 60%; 500 rising and 500 falling edges in 2 ms; no glitch candidates |
| Dual-output loopback capture, 20 MHz, 2 ms | Exactly 40,000 samples/channel; channel mapping confirmed |

The 16 input leads were floating during this validation. At a 1.6 V threshold all
inputs decoded low for the recorded 20 MHz capture. That result is recorded only
as a transport/data-integrity check, not as an electrical-input characterization.

## Remaining electrical validation

The two outputs now have a verified mid-band loopback measurement. Repeat near
the 1 Hz and 20 MHz limits, and with additional duty-cycle values, before
claiming accuracy across the complete advertised output range.

Hardware update, bootloader entry, MCU reset, and undocumented commands are out
of scope and were not sent.
