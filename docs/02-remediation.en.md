# 02 · Remediation: Three Steps and One Tail

**English** · [简体中文](02-remediation.md)

> Every step carries expected output; hand it to your AI assistant if needed. A restore point is recommended before registry changes.

---

## 0. Prep: open an admin PowerShell

Press the Windows key, type `powershell` → right-click the result → "**Run as administrator**" → click "Yes" on the prompt. The window title must contain "Administrator". Commands are pasted with a right-click and run with Enter.

---

## 1. Confirm it's this problem first

```powershell
Get-DeliveryOptimizationStatus | Where-Object { $_.NumPeers -gt 50 }
```

**Expected (affected)**: several jobs listed, `Status` `Paused`, `NumPeers` in the hundreds, downloaded bytes far below file size.
**Expected (not affected)**: no output, or normal jobs. If not affected, stop here — for generic pool-tag troubleshooting see the [official PoolMon docs](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/using-poolmon-to-find-a-kernel-mode-memory-leak).

---

## 2. Step 1: disable P2P (registry; cuts the fuel)

```powershell
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Name "DODownloadMode" -Value 0 -Type DWord
```

**Expected**: no errors. Equivalent to Settings → Windows Update → Delivery Optimization → "off", and more reliable for policy persistence.

**Impact**: updates still download, just from Microsoft servers directly; you stop seeding strangers (a net win for bandwidth and latency). **Do not disable the DoSvc service** — Windows Update depends on it.

---

## 3. Step 2: empty the seeding queue

```powershell
Delete-DeliveryOptimizationCache -Force
```

**Expected**: `Deleting... Successfully deleted Delivery Optimization cache`. Note: seeding sessions live in a separate state store; this command clears cache files — the final clearance of both is settled by the service restart below plus the reboot.

```powershell
sc.exe stop DoSvc
sc.exe start DoSvc
```

Re-check:

```powershell
Get-DeliveryOptimizationStatus
```

**Expected**: `No active Delivery Optimization download or upload jobs`.

---

## 4. Step 3: reboot and verify

After rebooting, Task Manager → Performance → Memory, "nonpaged pool" (bottom right) should fall back to a few hundred MB (this case: 4,138 → 975 MB). Watch the number over the following days:

- stable at a low level = case closed;
- climbing at ~0.3–0.8 GB/day = see the tail below.

---

## 5. The unresolved tail (recorded as-is)

After remediation this machine still shows a residual VAD leak of **~0.3–0.8 GB/day** (hundreds of thousands of nodes per day), unrelated to the seeding chain (it persists with the chain cut and the queue empty). Ruled out: DoSvc/P2P, Intel SUR, the HWiNFO monitoring driver, 360, NetEase components; not cleared: Huorong antivirus (its self-protection blocked the stop experiment). **Coexistence plan**: one natural reboot per week is entirely unnoticeable. The author chose to record rather than hunt it to the end — a 0.7 GB/day tail does no harm, and the clean-environment final audit (per-process VAD counts via kernel debugger) requires release-build symbols (unavailable on the preview channel); the cost-benefit doesn't match.

---

Prev: [01 · The chain](01-the-chain.en.md)
