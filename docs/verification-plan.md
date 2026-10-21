# Verification Plan — 授权环境实测（未执行）

2026-10-21 取证复核（DO-04）关闭条件中"授权现场与独立 PoolMon 交叉核对"部分。本计划为待办安排；执行前正文保持现有边界措辞。

## 1. 修复后脚本与 PoolMon 交叉核对

环境：任一 Windows x64 机器（需 64 位 Python + 管理员）。

| # | 步骤 | 通过标准 |
|---|---|---|
| 1 | `poolmon.exe -b`（WDK）与 `python scripts/pooltag.py snap.json` 同时刻各采一份 | 同标签字节数量级一致（±<5%） |
| 2 | `poolmon` 观察窗 60s 与 `python scripts/rate_probe.py VadS 60` | live/增长方向一致 |
| 3 | 记录：系统版本、Python 位数、两工具原始输出 | 存 evidence/，注明采集器版本 |

已知前提：脚本按 x64 布局（8 字节头 + 40 字节条目）解析；若换 32 位 Python 需重新校对偏移。

## 2. 复核"先处理什么"中的可选补强（DO-02/DO-03）

- 若需恢复"每秒查询次数"：采集带时间窗的 WMI-Activity 事件（EventLog 订阅或 wevtutil 循环），给出分母；否则正文保持"无法由 400 条无时间窗记录推出"。
- 若需证实净增速率：同会话多点 pooltag 快照序列（当前脚本已可产出），替代累计分配率口径。
