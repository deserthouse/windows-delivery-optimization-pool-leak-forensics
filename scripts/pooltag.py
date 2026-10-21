#!/usr/bin/env python3
"""Pool-tag snapshot: top-N tags by nonpaged usage (no WDK; NtQuerySystemInformation).

结构前提（x64）：SYSTEM_POOLTAG_INFORMATION = 8 字节头（ULONG Count + 4 填充）
+ 每条 40 字节 SYSTEM_POOLTAG（Tag[4] 自然序 + Pad + 计数字段按 ABI 布局）。
仅支持 64 位 Python（条目按 x64 固定偏移解析）。
2026-10-21 修复（取证复核 DO-04）：补 pathlib 导入（此前保存即 NameError）；
Tag 不再二次反转（内核缓冲区已是自然序，此前构造的 VadS 被打印成 SdaV）。
"""
import ctypes
import json
import struct
import sys
from pathlib import Path


def parse_tags(data):
    """解析 x64 SYSTEM_POOLTAG_INFORMATION 缓冲区 → [{tag,np_used,pg_used,np_allocs,np_frees}]"""
    (count,) = struct.unpack_from("<I", data, 0)
    tags = []
    for i in range(count):
        off = 8 + i * 40
        tag = data[off:off + 4].decode("ascii", "replace")  # 自然序，不再反转
        allocs, frees = struct.unpack_from("<II", data, off + 24)
        (np_used,) = struct.unpack_from("<Q", data, off + 32)
        (pg_used,) = struct.unpack_from("<Q", data, off + 16)
        tags.append(dict(tag=tag, np_used=np_used, pg_used=pg_used,
                         np_allocs=allocs, np_frees=frees))
    return tags


def query():
    ntdll = ctypes.windll.ntdll
    ret_len = ctypes.c_ulong(0)
    ntdll.NtQuerySystemInformation(0x16, None, 0, ctypes.byref(ret_len))
    buf = ctypes.create_string_buffer(ret_len.value + (1 << 20))
    st = ntdll.NtQuerySystemInformation(0x16, buf, ctypes.sizeof(buf), ctypes.byref(ret_len))
    if (st & 0xFFFFFFFF) != 0:
        raise SystemExit(f"query failed: {st:#x}")
    return parse_tags(buf.raw[:ret_len.value])


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "snapshot.json"
    tags = sorted(query(), key=lambda t: -t["np_used"])[:30]
    mb = 1048576
    print(f"{'tag':<8}{'NP_MB':>10}{'PG_MB':>10}{'live':>12}")
    for t in tags:
        print(f"{t['tag']:<8}{t['np_used'] / mb:>10.1f}{t['pg_used'] / mb:>10.1f}{t['np_allocs'] - t['np_frees']:>12,}")
    Path(out).write_text(json.dumps(tags, indent=1), encoding="utf-8")
    print(f"saved -> {out}")
