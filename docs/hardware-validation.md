# ATK Logic hardware validation: DL16

Date: 2026-09-02  
Host: Windows  
Device: ALIENTEK DL16, VID:PID `1a86:ffcc`, manufacturer `ATK`, product
`ATK-Logic-Analyzer`, USB serial `ATK22`

## Passed

| Test | Result |
|---|---|
| USB enumeration through bundled libusb backend | Device and descriptors found |
| Automatic device profile | Level 0 mapped to DL16; MCU 19, hardware revision 2 |
| Auto-profile D0/D1 capture, 1 MHz, 1 ms | DL16 selected; exactly 1,000 samples/channel |
| FPGA wake and endpoint drain | Repeated captures start from a clean boundary |
| D0, 1 MHz, 1 ms, ordinary mode | Exactly 1,000 samples |
| D0/D1, 1 MHz, 1 ms, ordinary mode | Exactly 1,000 samples/channel |
| D0–D15, 20 MHz, 1 ms, ordinary mode | Exactly 20,000 samples/channel |
| D0/D1, 1 MHz, 2 ms, RLE mode | Exactly 2,000 samples/channel after expansion |
| Signal OUT0, 1 kHz, 50%, 0.5 s | Command accepted; automatic stop succeeded |
| Signal OUT1, 2 kHz, 25%, 0.5 s | Command accepted; automatic stop succeeded |
| Stop all signal outputs | Command accepted |

The 16 input leads were floating during this validation. At a 1.6 V threshold all
inputs decoded low for the recorded 20 MHz capture. That result is recorded only
as a transport/data-integrity check, not as an electrical-input characterization.

## Remaining electrical validation

Connect OUT0 to a named digital input and OUT1 to another named input, keeping
grounds common. Capture at least 10 samples per shortest high/low interval and
compare measured frequency and duty against requested and tick-quantized values.
Repeat at low, middle, and high frequencies before claiming full output accuracy.

Hardware update, bootloader entry, MCU reset, and undocumented commands are out
of scope and were not sent.
