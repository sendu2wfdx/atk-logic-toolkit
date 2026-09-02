# ATK Logic Toolkit

ATK Logic Toolkit 是面向正点原子 DL16、DL16 Plus、DL32 和 DL32 Plus 的命令行采集与分析工具，并附带可用于 MCU 固件调试的 Codex Skill。它能够自动识别已连接的具体型号，按对应通道数、USB 代际、采样率和存储能力执行采集，避免套用错误的硬件参数。

本项目支持：

- 自动识别四款 ATK Logic USB 设备（VID `1a86`、PID `ffcc`）；
- 按正点原子开源 ATK-Logic 协议直接进行 USB 有限时长采集并保存 CSV；
- 导入 ATK-Logic 导出的 CSV，以及通用 VCD；
- 自动识别时间列、通道列和常见时间单位；
- 统计边沿、频率、占空比、毛刺候选、捕获时长和采样间隔；
- 解码 UART、I²C 和 SPI，并输出 JSON；
- 生成适合 MCU 固件分析的 Markdown 证据报告；
- 自带 `skills/atk-logic` Codex Skill。

## 支持的设备 profile

| Profile | 通道 | USB | Buffer 采样上限 | 硬件存储深度 | 测量带宽 | PWM | 状态 |
|---|---:|---:|---|---:|---:|---:|---|
| DL16 | 16 | 2.0 | 16ch / 250 MHz | 1 Gbit | 50 MHz | 2 | 实机验证 |
| DL16 Plus | 16 | 2.0 | 8ch / 1 GHz；16ch / 500 MHz | 3.5 Gbit | 200 MHz | 2 | 官方资料支持，待对应实机验证 |
| DL32 | 16 | 3.0 | 8ch / 1 GHz；12ch / 800 MHz；16ch / 500 MHz | 3.5 Gbit | 200 MHz | 4 | 官方资料支持，待对应实机验证 |
| DL32 Plus | 32 | 3.0 | 12ch / 1 GHz；15ch / 800 MHz；24ch / 500 MHz；30ch / 400 MHz；32ch / 250 MHz | 3.5 Gbit | 200 MHz | 4 | 官方资料支持，待对应实机验证 |
`atk-logic device info` 会读取官方上位机使用的两组身份数据：MCU 的 `level`，以及 FPGA 返回的名称、USB 代际和版本。名称会规范化后匹配 `DL16`、`DL16 Plus`、`DL32`、`DL32 Plus`；若 FPGA 身份包偶发超时，则从 USB 描述符读取 2.0/3.0 代际，再结合 `level` 区分普通版和 Plus。无法可靠识别时会明确报错，不会猜测型号。也可在采集时用 `--model dl16`、`--model dl16p`、`--model dl32` 或 `--model dl32p` 明确指定。只有 DL32 Plus 接受 D0–D31，并使用 16 字节触发通道掩码。

DL32 系列在 USB 3.0 下的 Stream 上限也已录入：DL32 为 3ch/1 GHz、6ch/500 MHz、12ch/250 MHz、16ch/125 MHz；DL32 Plus 另有 30ch/100 MHz、32ch/50 MHz。若降级连接到 USB 2.0，则按官方表中的较低档位限制（32ch 最低为 10 MHz）。当前直采命令使用 Buffer 模式；Stream 参数用于后续模式实现和设备能力校验。

> 直采已在真实 DL16（USB 序列号 `ATK22`）验证：单/双/16 通道、1/20 MHz、普通与 RLE 有限深度采集均通过。默认不包含 Bootloader 或固件升级功能。信号发生控制命令已完成设备实测；输出端实际波形仍需接回输入或示波器后才能完成电气验证。

## 安装

```bash
python -m pip install -e .
# 如需 USB 设备扫描
python -m pip install -e ".[usb]"
```

## 快速使用

```bash
atk-logic device scan
atk-logic device info
atk-logic capture capture.csv --channels D0,D1 --rate 20MHz --duration 10ms --threshold 1.6
atk-logic inspect capture.csv
atk-logic analyze capture.csv --out report.md
atk-logic uart capture.csv --channel D0 --baud 115200 --out uart.json
atk-logic i2c capture.csv --scl D0 --sda D1 --out i2c.json
atk-logic spi capture.csv --clk D0 --mosi D1 --miso D2 --cs D3 --mode 0 --out spi.json
atk-logic signal start --channel 0 --frequency 1kHz --duty 50
atk-logic signal start --channel 1 --frequency 2MHz --duty 25 --duration 2s
atk-logic signal stop --channel all
```

CSV 应包含时间列和数字通道列。ATK-Logic 常见头部（例如 `; Sample rate: 20 MHz`）会被保留为元数据。支持绝对采样表和仅在电平变化时记录的稀疏表。

```csv
Time[s],D0,D1
0.000000,1,1
0.000010,0,1
```

## MCU 分析建议

- UART：采样率至少为波特率的 8 倍，推荐 10–20 倍；先确认空闲电平和是否反相。
- I²C：同时采集 SCL/SDA；START 是 SCL 为高时 SDA 下降，STOP 相反。
- SPI：记录 CLK、CS、MOSI，若要观察读回再加 MISO；必须确认 mode、位序和 CS 有效电平。
- 所有推断都应引用时间戳、通道和原始字节。工具报告会区分“观测事实”和“解释”。

DL16 系列的两路信号发生输出编号为 0 和 1，支持 1 Hz–20 MHz、1%–99% 占空比。DL32 系列硬件规格为四路 PWM；当前已验证并开放与 DL16 协议相同的前两路，另外两路在取得对应实机前不发送未经验证的控制值。`--duration` 会在指定时间后自动停止该路输出，适合安全测试。信号输出不是输入通道；做回环验证时需要用跳线把输出明确接到输入并共地。

## Skill 安装

把 `skills/atk-logic` 复制到 Codex skills 目录，或直接从本仓库安装该 Skill。Skill 会调用仓库内的 `atk-logic` 命令，并指导设备识别、接线、采样质量检查、协议解码和固件行为归因。

## 兼容与来源

设备协议依据正点原子开源的 ATK-Logic 项目实现，因此本项目采用 GPL-3.0-or-later。它不是正点原子的官方产品。ALIENTEK、正点原子、DL16 是其各自权利人的名称或商标。

## 致谢与许可

协议、USB 数据重排和配置字段来自 [alientek-openedv/atk-logic](https://github.com/alientek-openedv/atk-logic)，原项目许可为 GPL-3.0-or-later。详见 `COPYING` 和 `NOTICE.md`。

真实设备回归记录见 [`docs/hardware-validation.md`](docs/hardware-validation.md)。
