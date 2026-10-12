#!/usr/bin/env python3
"""PreToolUse (matcher Write|Edit|Bash|mcp__remote-devices__device_bash|device_commit_files):
ไฟล์ใน 01_master / 02_historys / 03_report_files แก้ได้ผ่าน scripts/nnp_cli.py เท่านั้น"""
import re

from _common import DATA_SUBDIRS, block, data_dirs, heartbeat, read_input

d = read_input()
heartbeat("PreToolUse:files")
tool = d.get("tool_name", "")
a = d.get("tool_input") or {}
dirs = data_dirs()


def in_data(path: str) -> bool:
    p = (path or "").replace("\\", "/")
    return any(f"{x}/{s}" in p for x in dirs for s in DATA_SUBDIRS)


if tool in ("Write", "Edit", "NotebookEdit"):
    if in_data(a.get("file_path", "")):
        block("ห้ามเขียนไฟล์ในโฟลเดอร์ข้อมูลโดยตรง — ใช้ python3 scripts/nnp_cli.py (begin/apply) เท่านั้น")
elif tool.endswith("device_commit_files"):
    for f in a.get("files", []):
        if in_data(f.get("devicePath", "")):
            block("ห้าม commit ไฟล์เข้าโฟลเดอร์ข้อมูลโดยตรง — ใช้ scripts/nnp_cli.py")
elif tool == "Bash" or tool.endswith("device_bash"):
    cmd = a.get("command", "")
    if "nnp_cli.py" in cmd:
        if not re.search(r"nnp_cli\.py\s+(check-env|status)\b", cmd):
            if not (re.search(r"--org\s+(oag|mwd)\b", cmd) and re.search(r"--month\s+\d{4}-\d{2}\b", cmd)):
                block("คำสั่ง nnp_cli.py ต้องระบุ --org <oag|mwd> และ --month YYYY-MM ให้ชัดเจนเสมอ")
    elif any(f"{x}/{s}" in cmd for x in dirs for s in DATA_SUBDIRS):
        writes = re.search(r"(>|>>|\btee\b|\bmv\b|\bcp\b|\brm\b|\bsed\s+-i|\bunlink\b|\.save\(|\.write\(|shutil|os\.remove|os\.rename)", cmd)
        if writes:
            block("คำสั่งนี้ดูเหมือนแก้/ลบ/ย้ายไฟล์ในโฟลเดอร์ข้อมูลโดยไม่ผ่าน nnp_cli.py — ห้าม (อ่านอย่างเดียวได้)")
