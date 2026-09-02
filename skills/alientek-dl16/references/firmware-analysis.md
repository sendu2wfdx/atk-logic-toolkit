# Firmware correlation

Use three evidence levels:

- **Observed:** directly present in the capture, such as an edge at a timestamp, a valid UART byte, I²C ACK, or SPI word under stated parameters.
- **Correlated:** supported by both waveform and firmware evidence, such as a decoded register write matching a constant referenced by one function near the reproduced event.
- **Hypothesis:** plausible but not uniquely established, such as assigning an undocumented byte to a state transition.

For each important claim, retain the capture filename/hash, channel map, decoder parameters, timestamp range, decoded bytes, and relevant source/function/address. Prefer differential experiments: reproduce a baseline, change one firmware input or setting, and compare the affected transactions.

Do not equate temporal proximity with causation. Interrupts, DMA, buffering, retries, and transport framing can separate code execution from observed wire activity. When binaries lack symbols, use call graphs, MMIO constants, peripheral base addresses, string references, and controlled traces together; avoid assigning function names from a single waveform pattern.

