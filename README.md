# ALIENTEK DL16 Toolkit

面向 MCU 固件逆向与调试的正点原子逻辑分析仪辅助工具和 Codex Skill。默认设备为 **DL16（16 通道）**。

本项目支持：

- 识别 DL16 USB 设备（VID `1a86`、PID `ffcc`）；
- 按正点原子开源 ATK-Logic 协议直接进行 USB 有限时长采集并保存 CSV；
- 导入 ATK-Logic 导出的 CSV，以及通用 VCD；
- 自动识别时间列、通道列和常见时间单位；
- 统计边沿、频率、占空比、毛刺候选、捕获时长和采样间隔；
- 解码 UART、I²C 和 SPI，并输出 JSON；
- 生成适合 MCU 固件分析的 Markdown 证据报告；
- 自带 `skills/alientek-dl16` Codex Skill。

> 直采已在真实 DL16（USB 序列号 `ATK22`）验证：单/双/16 通道、1/20 MHz、普通与 RLE 有限深度采集均通过。默认不包含 Bootloader 或固件升级功能。信号发生控制命令已完成设备实测；输出端实际波形仍需接回输入或示波器后才能完成电气验证。

## 安装

```bash
python -m pip install -e .
# 如需 USB 设备扫描
python -m pip install -e ".[usb]"
```

## 快速使用

```bash
dl16 inspect capture.csv
dl16 analyze capture.csv --out report.md
dl16 uart capture.csv --channel D0 --baud 115200 --out uart.json
dl16 i2c capture.csv --scl D0 --sda D1 --out i2c.json
dl16 spi capture.csv --clk D0 --mosi D1 --miso D2 --cs D3 --mode 0 --out spi.json
dl16 device scan
dl16 capture capture.csv --channels D0,D1 --rate 20MHz --duration 10ms --threshold 1.6
dl16 signal start --channel 0 --frequency 1kHz --duty 50
dl16 signal start --channel 1 --frequency 2MHz --duty 25 --duration 2s
dl16 signal stop --channel all
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

DL16 的两路信号发生输出编号为 0 和 1，支持 1 Hz–20 MHz、1%–99% 占空比。`--duration` 会在指定时间后自动停止该路输出，适合安全测试。信号输出不是输入通道；做回环验证时需要用跳线把输出明确接到某个 D0–D15 输入并共地。

## Skill 安装

把 `skills/alientek-dl16` 复制到 Codex skills 目录，或直接从本仓库安装该 Skill。Skill 会调用仓库内的 `dl16` 命令，并指导接线、采样质量检查、协议解码和固件行为归因。

## 兼容与来源

设备协议依据正点原子开源的 ATK-Logic 项目实现，因此本项目采用 GPL-3.0-or-later。它不是正点原子的官方产品。ALIENTEK、正点原子、DL16 是其各自权利人的名称或商标。

## 致谢与许可

协议、USB 数据重排和配置字段来自 [alientek-openedv/atk-logic](https://github.com/alientek-openedv/atk-logic)，原项目许可为 GPL-3.0-or-later。详见 `COPYING` 和 `NOTICE.md`。

真实设备回归记录见 [`docs/hardware-validation.md`](docs/hardware-validation.md)。
