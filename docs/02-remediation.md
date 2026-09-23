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

**预期（中招）**：列出若干任务，`Status` 为 `Paused`、`NumPeers` 一两百、下载字节远小于文件大小。
**预期（没中）**：无输出或任务正常。没中的读者请勿继续——你的问题在别处，池标签排查的通用方法见[微软官方 PoolMon 文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/using-poolmon-to-find-a-kernel-mode-memory-leak)。

---

## 2. 第一步：关闭 P2P 下载（注册表，斩断燃料）

```powershell
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Name "DODownloadMode" -Value 0 -Type DWord
```

**预期**：无报错。此设置等价于设置 → Windows 更新 → 交付优化 → 关闭"允许从其他电脑下载"，且对后续策略生效更可靠。

**影响**：更新照常下载，只是来源改为微软服务器直连；不再给陌生 peer 做种（对带宽和延迟是净收益）。**不要禁用 DoSvc 服务**——Windows 更新依赖它。

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

处置后本机仍有约 **0.3~0.8 GB/天**的 VAD 残余泄漏（每天几十万个节点），与本案的做种链无关（链条已断、队列已空后依然存在）。已排除：DoSvc/P2P、Intel SUR、HWiNFO 监控驱动、360、网易组件；嫌疑未清：火绒（自保护阻止了停用实验）。**共存方案**：每周自然重启一次即可完全无感。笔者选择记录而非追杀到底——0.7 GB/天的尾巴不构成危害，而干净环境下的终审（内核调试器逐进程 VAD 计数）需要正式版符号（预览通道不可得），成本收益不匹配。

---

上一篇：[01 · 因果链](01-the-chain.md)
