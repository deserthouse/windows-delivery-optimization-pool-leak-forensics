# 02 · 修复：三步与一个尾巴

**简体中文** · [English](02-remediation.en.md)

> 每步都带预期输出；看不懂命令行可交给 AI 助手照单执行。修改注册表前建议创建还原点。

---

## 0. 准备：打开"管理员 PowerShell"

按 Windows 键输入 `powershell` → 右键搜索结果 → "**以管理员身份运行**" → 弹窗点"是"。窗口标题带"管理员"三个字才算。命令都是复制后在窗口里右键粘贴、回车执行。

---

## 1. 先确认是不是这个问题

```powershell
Get-DeliveryOptimizationStatus | Where-Object { $_.NumPeers -gt 50 }
```

**这是筛查线索，不是确诊（2026-10-21 限定）**：`NumPeers` 是服务端返回的总 peer 数（Internet 连接数另见 `InternetConnectionCount`，两者不可互换）；`Paused` + 高 peer + 下载停滞**只说明存在类似现场**——没有这些现象也不能排除池增长另有原因。命中者继续对照；未命中且池仍异常的，走通用池标签排查：[微软官方 PoolMon 文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/using-poolmon-to-find-a-kernel-mode-memory-leak)。

---

## 2. 第一步：关闭 P2P 下载（注册表，斩断燃料）

```powershell
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Name "DODownloadMode" -Value 0 -Type DWord
```

**预期**：无报错。此设置等价于设置 → Windows 更新 → 交付优化 → 关闭"允许从其他电脑下载"，且对后续策略生效更可靠。

**影响（按官方语义限定）**：DODownloadMode=0 = HTTP 无 P2P；仍可使用 Connected Cache，不等于"仅微软服务器"。不再给陌生 peer 做种；带宽/延迟净收益因网络而异（未做对照测量）。**不要禁用 DoSvc 服务**——Windows 更新依赖它。

---

## 3. 第二步：清空做种队列

```powershell
Delete-DeliveryOptimizationCache -Force
```

**预期**：`Deleting... Successfully deleted Delivery Optimization cache`。注意：实测做种会话存储在独立状态库，本命令清的是缓存文件；两者的最终清除都以下一步的服务重启 + 重启电脑为准。

```powershell
sc.exe stop DoSvc
sc.exe start DoSvc
```

复测：

```powershell
Get-DeliveryOptimizationStatus
```

**预期**：`No active Delivery Optimization download or upload jobs`（无任务）。

---

## 4. 第三步：重启并验证

重启电脑后，任务管理器 → 性能 → 内存，右下角"**非分页缓冲池**"应回落到几百 MB（本案实测：4,138 → 975 MB）。此后数天观察该数值：

- 稳定在低位 = 结案；
- 以约 0.3~0.8 GB/天缓慢爬升 = 见下方"未结的尾巴"。

---

## 5. 未结的尾巴（如实记录）

处置后本机仍有约 **0.3~0.8 GB/天**的 VAD 残余泄漏（`VadS` 短节点约 52/秒，`daV` 长节点约 10/秒，双标签同源；每天几十上百万个节点），做种链断开、队列清空后依然存在（残余与本案的**同源性未证实**——已对照排除：DoSvc/P2P、Intel SUR、HWiNFO 监控驱动、360、网易组件；嫌疑未清：火绒，自保护阻止了停用实验）。**共存建议（不是安全保证）**：是否重启看**可用内存水位、净增速率与工作负载**——evidence/pooltag-timeline 在 2 天 13 小时时已记池 2,637 MB、可用内存 2.3 GB 并建议重启，"每周一次完全无感"与该记录不符，撤回。终审需要正式版符号（预览通道 build 的符号获取失败记录未留档，仅记"尝试未果"）。

---

上一篇：[01 · 因果链](01-the-chain.md)
