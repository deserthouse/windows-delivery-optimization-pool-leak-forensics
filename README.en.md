# A Seeding-Induced Kernel-Pool Leak in Windows Delivery Optimization

**English** · [简体中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-0078D4.svg)](LICENSE)

**A kernel-memory leak triggered by "seeding": Delivery Optimization (DoSvc) stuck jobs held 258–299 internet peers each, polled the NIC statistics via WMI a thousand times per second, every query failed on quota exhaustion (0x80041032) and was retried without backoff — accumulating 4.1 GB of kernel VAD leak over 5 days. The fix is turning P2P off; no driver is touched.**

> **Note for non-expert readers**: if your machine shows "Task Manager looks fine, yet the whole system stutters — reboot helps, it comes back days later", start with the [symptom check](README.md#症状对照) and then follow the [remediation doc](docs/02-remediation.en.md). You can hand this repo's link to your AI assistant and have it follow the steps — every step carries expected output.

---

## Contents

- [What this is](#what-this-is)
- [Symptom check](#symptom-check)
- [Findings at a glance](#findings-at-a-glance)
- [Docs](#docs)
- [Evidence discipline](#evidence-discipline)
- [Disclaimer](#disclaimer)

---

## What this is

A Windows machine (i7 / 32 GB / Win11 preview channel) saw its nonpaged kernel memory climb to **4.1 GB over 5 days** with no process in Task Manager to explain it, accompanied by system-wide intermittent freezes (most visible in games; tens of seconds, self-recovering).

**The author traced the complete causal chain** — four links, each measured:

```
A Windows Update download job stuck Paused (22.8 MB, 3.5% downloaded, never cleaned up)
  → the job holds 258–299 internet-peer connections (this machine was seeding the world; 3 jobs, 800+ connections)
    → per-connection traffic statistics → a thousand+ WMI NIC-statistics queries per second
      → WMI quota exhausted (0x80041032); every query fails
        → DoSvc retries in a no-backoff loop; each retry spawns short-lived processes
          → kernel VAD nodes leak (16 million in 5 days ≈ 4.1 GB)
            → GPU/network starve for kernel memory → freezes and in-game stalls
```

**Difference from prior community reports**: each link individually is documented (Microsoft's official [DO troubleshooting](https://learn.microsoft.com), matching [WMI quota-loop cases](https://community.spiceworks.com), scattered VadS-leak discussions), but **the complete chain has not been published**. One neighbor to draw a line against: the [KB5072033 DO memory issue](https://support.bmileisure.com) (2025) was a patch bug — a completely different mechanism from the seeding chain here.

Companion repos (same family of cases): [OMEN dual-leak forensics](https://github.com/deserthouse/omen-gaming-hub-pool-leak-forensics) · [AlibabaProtect](https://github.com/deserthouse/alibabaprotect-forensics).

---

## Findings at a glance

| # | Finding | Evidence | Strength |
|:---:|---|---|:---:|
| 1 | Nonpaged pool reached 4,138 MB in 5 days; the `VadS` tag alone held 1,478 MB / 16.15 M nodes | pool-tag snapshots (evidence/pooltag-timeline) | ✅ measured (session transcript) |
| 2 | The leak ran at a constant rate since boot (95.44 M allocations ÷ 432,000 s ≈ 220/s) | allocation-count back-calculation | ✅ measured (session transcript) |
| 3 | 3 DO jobs stuck Paused — 0.79 MB downloaded of 22.8 MB — each holding 250–299 internet peers, 4.4 MB already uploaded | full `Get-DeliveryOptimizationStatus` field dump | ✅ measured (session transcript) |
| 4 | 209 of 400 WMI-Activity log entries came from DoSvc — all the same Realtek NIC-statistics query, all returning 0x80041032 | event-log tally | ✅ measured (session transcript) |
| 5 | Stop-one-service-at-a-time contrast: leak persisted after stopping esrv/Vantage/NVDisplay; after stopping DoSvc the rate collapsed from a 17,410/90 s peak | causal contrast experiment | ✅ measured (session transcript) |
| 6 | After disabling P2P (DODownloadMode=0) the seeding queue emptied; 800+ peer connections gone | post-remediation check | ✅ measured (session transcript) |
| 7 | After reboot the nonpaged pool returned to 975 MB (normal level) | post-reboot snapshot | ✅ measured (session transcript) |
| 8 | A residual VAD leak of ~0.3–0.8 GB/day remains; source unidentified | multi-window rate measurements | ⚠️ unresolved (see doc 02 §4) |
| 9 | One day after remediation: DODownloadMode=0 in effect, zero DO jobs, no recurrence | on-machine recheck (2026-09-23) | ✅ measured (persisted) |

Both mechanisms were located and remediated — the fix = registry-disable P2P + clear the seeding queue + reboot, all in the [remediation doc](docs/02-remediation.en.md); the residual tail (#8) is documented, unresolved, and coexists harmlessly with a once-a-week reboot.

---

## Symptom check

Both of these matching means it's probably this case:

1. Task Manager → Performance → Memory shows a **nonpaged pool** in the GB range that keeps climbing; process memory normal, CPU idle, disks idle;
2. System-wide intermittent freezes (most visible in games: everything locks for tens of seconds, then recovers), relieved by rebooting and returning days later.

One command to confirm (the [scripts](scripts/) are read-only; Python as admin):

```bash
python scripts/pooltag.py snapshot.json
```

`VadS` at GB scale in the top list → follow this repo's process; also check the Delivery Optimization jobs (command in doc 02).

---

## Docs

| Doc | What's in it |
|---|---|
| [01 · The chain](docs/01-the-chain.en.md) · [中文](docs/01-the-chain.md) | the four links with evidence each: seeding jobs, the WMI loop, the VAD leak, the freeze mechanism |
| [02 · Remediation](docs/02-remediation.en.md) · [中文](docs/02-remediation.md) | disable P2P, clear the queue, verify; the unresolved tail and the coexistence plan |
| [evidence/](evidence/) | evidence files (with transcript labeling) |
| [scripts/](scripts/) | read-only diagnostic scripts (pool-tag snapshot / rate probe; no WDK) |
| [DISCLAIMER.md](DISCLAIMER.md) | scope statement and AI usage statement |

---

## Evidence discipline

Same rules as the author's other three forensic repos:

1. **Every conclusion ships with reproducible evidence** — command, raw output, or data table;
2. **Statement grades**: ✅ measured (persisted) / ⚠️ unresolved or inferred (basis stated);
3. **Special note on "session transcript"**: the investigation happened while the problem was live, and most raw outputs were not persisted at capture time (the source state vanished after remediation, so it cannot be re-collected). Data transcribed from the investigation session is labeled "session transcript" in the findings table; every number was a stable value across repeated measurements at the time. On-machine rechecks from 2026-09-23 onward are persisted per the repo's standard (#9);
4. **Correlation ≠ causation** — the stop-one-service-at-a-time contrast (#5) is what closed the case; temporal coincidence was never the basis.

---

## Disclaimer

See [DISCLAIMER.md](DISCLAIMER.md). In short: for diagnosis and research on devices you own and administer only; no vendor affiliation; single-machine data; the remediation modifies the registry — create a restore point first.

## License

[MIT](LICENSE)
