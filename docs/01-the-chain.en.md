# 01 · The Chain: Four Links of Evidence

**English** · [简体中文](01-the-chain.md)

Each link: the symptom, the measurement, and why it holds. All numbers are stable values from repeated measurements during the investigation session (2026-09-21/22); transcript labeling per the README's evidence-discipline section.

---

## Link 1: the stuck seeding jobs

**Symptom**: `Get-DeliveryOptimizationStatus` showed 3 download jobs, all `Paused`, each holding 250–299 internet peers, near-zero download bytes but growing upload bytes.

Key job, full fields (excerpt; complete dump in `evidence/do-jobs-before.txt`):

```
FileId        : bca53c4f… (a 22.8 MB Windows Update package)
Status        : Paused
TotalBytesDownloaded : 793,779      ← 3.5%
BytesFromHttp : 793,779
InternetConnectionCount : 258
BytesToInternetPeers   : 4,427,647  ← 4.4 MB already uploaded to strangers
DownloadMode  : Internet
Caller        : WU Client Download
```

**Why it holds**: a job stuck Paused is never cleaned up (it lingers until expiry), yet its peer connections and uploads continue — your machine is distributing a 3.5%-downloaded update fragment to the world. Every connection needs continuous traffic accounting.

**Why cache-clear/reboot don't help**: the seeding sessions persist in DO's state store — not cache files, and they survive reboots (measured: identical FileIds returned after reboot).

---

## Link 2: the WMI quota death-loop

**Symptom**: of 400 recent WMI-Activity entries, **209 came from DoSvc** (runner-up: 36) — all the same query, all failing:

```
SELECT * FROM MSFT_NetAdapterStatisticsSettingData
WHERE Name = 'Realtek Gaming 2.5GbE Family Controller'
ResultCode = 0x80041032   ← WMI quota exhausted
```

**Why it holds**: 800+ connections × traffic-accounting needs → a thousand+ NIC-counter queries per second; once WMI's per-account quota fills, every query is refused; DoSvc's retry logic has no backoff (fail → retry immediately), closing the loop. Every retry walks the full path — COM activation, the WMI service, short-lived provider processes, driver counter reads — all in vain, yet every step creates and destroys kernel objects.

---

## Link 3: the VAD leak

**Symptom**: nonpaged pool at 4,138 MB after 5 days; pool-tag audit pinned `VadS` (kernel virtual-address-descriptor short nodes): 1,478 MB / **16.15 million live nodes**, plus a `daV` family at 688 MB. After remediation and reboot: 975 MB.

**Why it holds**: the link-2 pipeline (a thousand+ object create/destroy cycles per second) has a reclamation gap — 840 million allocations against 835 million frees, netting +50–200 nodes per second. Three clinchers:

1. **Attributable to no user process**: enumerating per-process virtual-memory regions system-wide totals <400k regions — nowhere near 16 million nodes;
2. **The leak rate tracks system activity**: nearly zero while the CPU is busy (e.g., a full-load build), full speed when idle — classic low-priority background behavior;
3. **The stop-one-service contrast**: the leak persisted after stopping Intel SUR / Lenovo Vantage / the NVIDIA container; **after stopping DoSvc the rate collapsed from a 17,410/90 s peak** — the case-closing experiment.

---

## Link 4: the system-wide freezes

**Symptom**: the nonpaged pool is required memory for GPU drivers (DMA buffers), the network stack, and disk IO; with 4.1 GB of dead nodes filling it, high-demand moments (game loading, heavy traffic) cross the threshold → allocations block → rendering stalls → the compositor waits on the GPU → full-screen freeze. Tens of seconds later the memory manager squeezes out fragmented space — self-healing, leaving no crash record.

**The gamer's view of the same case**: freezes always strike during games (demand peaks meet the water line), last tens of seconds and self-recover (the pulse recedes), and leave almost no log trace (the error-reporting service itself is on the freeze list). This machine's timeline has matching scenes: a shell crash 8 minutes after a game session ended, Task Manager freezing to death, and one anti-cheat-driver green screen (a typical casualty shape during memory exhaustion).

---

## Why the fix is "turn P2P off"

The chain's fuel is the peer connections — no peers, no traffic accounting, and the loop physically cannot sustain itself. Hence:

- no driver is touched (in this case every driver is innocent);
- DoSvc itself is not disabled (Windows Update depends on it; disabling is a bad trade);
- setting P2P to "HTTP only" empties the seeding queue.

Concrete steps in [02 · Remediation](02-remediation.en.md).

---

Next: [02 · Remediation](02-remediation.en.md)
