#!/usr/bin/env python3
"""SessionStart: บันทึก heartbeat + เตือนบริบท (ให้ /init-nnp-counter-skills ตรวจได้ว่า hooks ทำงาน)"""
import json

from _common import heartbeat, read_input, tickets

read_input()
heartbeat("SessionStart")
msg = ("โปรเจกต์ nnp-counter: อ่าน CLAUDE.md ก่อนทำงาน. คำสั่ง: /nnp-counter-oag|mwd|all {YYYY-MM}, /init-nnp-counter-skills. "
       "ต้องระบุองค์กรและเดือนทุกครั้ง ถ้าไม่ระบุเดือนให้ถามกลับ")
act = tickets()
if act:
    msg += " | งานค้าง: " + ", ".join(f"{t['org']} {t['ym']} ({t['state']})" for t in act)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
