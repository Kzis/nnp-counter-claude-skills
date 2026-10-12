#!/usr/bin/env python3
"""Stop (เซสชันหลัก): ห้ามจบงานถ้ามี ticket ที่ยังไม่ verified (ภายใน 3 ชม.) — ยกเลิกด้วยคำสั่ง abort"""
import json
import sys

from _common import heartbeat, read_input, tickets

d = read_input()
heartbeat("Stop")
if d.get("stop_hook_active"):
    sys.exit(0)                                   # กัน loop: เตือนครั้งเดียว
open_ = tickets()
if open_:
    items = ", ".join(f"{t['org']} {t['ym']} (ขั้น {t['state']}{', dry-run' if t.get('dry_run') else ''})" for t in open_)
    print(json.dumps({"decision": "block", "reason":
        f"ยังมีงานที่ไม่ผ่าน verify: {items}. ทำให้จบถึง verify หรือถ้าตั้งใจยกเลิก ให้รัน "
        f"python3 scripts/nnp_cli.py abort --org <org> --month <YYYY-MM> แล้วรายงานผู้ใช้ว่าทำไมไม่เสร็จ"}, ensure_ascii=False))
