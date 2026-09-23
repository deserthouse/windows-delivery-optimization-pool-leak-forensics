#!/usr/bin/env python3
"""Rate probe: watch one pool tag's live-object growth over a window."""
import ctypes
import struct
import sys
import time


def live(needle):
    ntdll = ctypes.windll.ntdll
    ret_len = ctypes.c_ulong(0)
    ntdll.NtQuerySystemInformation(0x16, None, 0, ctypes.byref(ret_len))
    buf = ctypes.create_string_buffer(ret_len.value + (1 << 20))
    st = ntdll.NtQuerySystemInformation(0x16, buf, ctypes.sizeof(buf), ctypes.byref(ret_len))
    if (st & 0xFFFFFFFF) != 0:
        raise SystemExit("query failed")
    data = buf.raw[:ret_len.value]
    (count,) = struct.unpack_from("<I", data, 0)
    for i in range(count):
        off = 8 + i * 40
        if data[off:off + 4] == needle:
            a, f = struct.unpack_from("<II", data, off + 24)
            (np_used,) = struct.unpack_from("<Q", data, off + 32)
            return a - f, np_used
    return None, 0


if __name__ == "__main__":
    disp = sys.argv[1] if len(sys.argv) > 1 else "VadS"
    needle = disp.encode()[::-1]
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    a, u1 = live(needle)
    time.sleep(window)
    b, u2 = live(needle)
    if a is None:
        print("tag not found")
    else:
        print(f"{disp}: live {a:,} -> {b:,} over {window}s (delta {b - a:+,}, used {(u2 - u1) / 1024:+.1f} KB)")
