#!/usr/bin/env python3
"""Pool-tag snapshot: top-N tags by nonpaged usage (no WDK; NtQuerySystemInformation)."""
import ctypes
import json
import struct
import sys


def query():
    ntdll = ctypes.windll.ntdll
    ret_len = ctypes.c_ulong(0)
    ntdll.NtQuerySystemInformation(0x16, None, 0, ctypes.byref(ret_len))
    buf = ctypes.create_string_buffer(ret_len.value + (1 << 20))
    st = ntdll.NtQuerySystemInformation(0x16, buf, ctypes.sizeof(buf), ctypes.byref(ret_len))
    if (st & 0xFFFFFFFF) != 0:
        raise SystemExit(f"query failed: {st:#x}")
    data = buf.raw[:ret_len.value]
    (count,) = struct.unpack_from("<I", data, 0)
    tags = []
    for i in range(count):
        off = 8 + i * 40
        tag = data[off:off + 4][::-1].decode("ascii", "replace")
        allocs, frees = struct.unpack_from("<II", data, off + 24)
        (np_used,) = struct.unpack_from("<Q", data, off + 32)
        (pg_used,) = struct.unpack_from("<Q", data, off + 16)
        tags.append(dict(tag=tag, np_used=np_used, pg_used=pg_used, np_allocs=allocs, np_frees=frees))
    return tags


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "snapshot.json"
    tags = sorted(query(), key=lambda t: -t["np_used"])[:30]
    mb = 1048576
    print(f"{'tag':<8}{'NP_MB':>10}{'PG_MB':>10}{'live':>12}")
    for t in tags:
        print(f"{t['tag']:<8}{t['np_used'] / mb:>10.1f}{t['pg_used'] / mb:>10.1f}{t['np_allocs'] - t['np_frees']:>12,}")
    Path(out).write_text(json.dumps(tags, indent=1), encoding="utf-8")
    print(f"saved -> {out}")
