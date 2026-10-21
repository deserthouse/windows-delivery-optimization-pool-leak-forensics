#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DO-04 修复的合成缓冲区测试（取证复核关闭条件）。

构造多标签 x64 SYSTEM_POOLTAG 合成缓冲区：
  parse_tags 解析出的 tag 应为自然序（VadS 而非 SdaV）；
  pooltag 保存 JSON 可成功（pathlib 导入）；
  rate_probe.parse_one 用自然序 needle 能查到并对账 VadS 的 live 值。
"""
import importlib.util
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import pooltag          # noqa: E402
import rate_probe       # noqa: E402

FAIL = []
def check(label, cond):
    print("  [%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAIL.append(label)

def entry(tag, allocs, frees, np_used, pg_used=0):
    e = bytearray(40)
    e[0:4] = tag.encode("ascii")            # 自然序
    struct.pack_into("<II", e, 24, allocs, frees)
    struct.pack_into("<Q", e, 32, np_used)
    struct.pack_into("<Q", e, 16, pg_used)
    return bytes(e)

buf = struct.pack("<I", 3) + b"\x00" * 4 + entry("VadS", 100, 40, 1500 << 20) \
      + entry("Cont", 10, 9, 2 << 20) + entry("MmSt", 7, 7, 1 << 20)

tags = pooltag.parse_tags(buf)
check("多标签解析数量", len(tags) == 3)
check("VadS 自然序（非 SdaV）", tags[0]["tag"] == "VadS")
check("字段对账 allocs/frees/np_used",
      tags[0]["np_allocs"] == 100 and tags[0]["np_frees"] == 40
      and tags[0]["np_used"] == 1500 << 20)

# 保存 JSON（DO-04 的 NameError 反例）
tmp = os.path.join(tempfile.mkdtemp(prefix="wdo_"), "snap.json")
pooltag.Path(tmp).write_text(json.dumps(tags[:1]), encoding="utf-8")
check("Path 保存 JSON 成功", json.load(open(tmp, encoding="utf-8"))[0]["tag"] == "VadS")

# rate_probe 对账
live, used = rate_probe.parse_one(buf, b"VadS")
check("rate_probe 查到 VadS（自然序 needle）", live == 60 and used == 1500 << 20)
live_miss, _ = rate_probe.parse_one(buf, b"SdaV")
check("反转序 needle 不再命中（防回归）", live_miss is None)

print("")
print("FAILED: %s" % FAIL if FAIL else "ALL PASS")
sys.exit(1 if FAIL else 0)
