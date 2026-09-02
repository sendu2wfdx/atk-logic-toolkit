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

> 直采实现已按官方 GPL 源码复现，但当前开发环境没有连接 DL16，因此标记为 **source-verified / hardware-unverified**。默认只执行普通采集命令，不包含复位、Bootloader 或固件升级功能。首次使用请先短时采集并与 ATK-Logic 的同参数结果比对。

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

## Skill 安装

把 `skills/alientek-dl16` 复制到 Codex skills 目录，或直接从本仓库安装该 Skill。Skill 会调用仓库内的 `dl16` 命令，并指导接线、采样质量检查、协议解码和固件行为归因。

## 兼容与来源

设备协议依据正点原子开源的 ATK-Logic 项目实现，因此本项目采用 GPL-3.0-or-later。它不是正点原子的官方产品。ALIENTEK、正点原子、DL16 是其各自权利人的名称或商标。

## 致谢与许可

协议、USB 数据重排和配置字段来自 [alientek-openedv/atk-logic](https://github.com/alientek-openedv/atk-logic)，原项目许可为 GPL-3.0-or-later。详见 `COPYING` 和 `NOTICE.md`。

