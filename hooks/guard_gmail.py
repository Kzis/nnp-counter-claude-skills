#!/usr/bin/env python3
"""PreToolUse (matcher mcp__Gmail__.*): Gmail ใช้ได้เฉพาะอ่าน/ติด label ภายใต้ ticket ที่เปิดอยู่ และ query ต้องตรง ticket"""
from _common import LABEL_RE, READ_TOOLS, block, heartbeat, read_input, tickets

d = read_input()
heartbeat("PreToolUse:gmail")
tool = d.get("tool_name", "")
name = tool.rsplit("__", 1)[-1]
args = d.get("tool_input") or {}
act = tickets()

if name in ("list_labels", "get_message", "get_thread"):
    pass
elif name == "search_threads":
    q = (args.get("query") or "").strip()
    if not any(q == t.get("query") for t in act):
        block(f"search_threads ต้องใช้ gmail_query ที่ begin คืนมาตามตัวอักษร (ไม่พบ ticket ที่ตรงกับ query นี้). "
              f"ticket ที่เปิดอยู่: {[(t['org'], t['ym']) for t in act] or 'ไม่มี — รัน begin ก่อน'}")
elif name == "create_label":
    n = args.get("name", "")
    ok = [t for t in act if not t.get("dry_run") and t.get("label") == n]
    if not LABEL_RE.match(n) or not ok:
        block(f"สร้าง label '{n}' ไม่ได้: ชื่อต้องเป็น <org>-YYYY-MM และตรงกับ ticket รอบจริงที่เปิดอยู่ (dry-run สร้าง label ไม่ได้)")
elif name == "label_message":
    ok = [t for t in act if not t.get("dry_run") and t.get("state") in ("applied", "labeled")]
    if not ok:
        block("label_message ทำได้เฉพาะหลัง apply ของรอบจริง (ไม่ใช่ dry-run) — ไม่พบ ticket ที่พร้อมติด label")
elif name == "label_thread":
    block("label_thread ห้ามใช้ — thread หนึ่งมีข้อความหลายเดือน ต้องติดทีละข้อความด้วย label_message")
else:
    block(f"เครื่องมือ Gmail '{name}' ไม่อนุญาตในระบบนี้ (อนุญาต: {sorted(READ_TOOLS)} + create_label, label_message)")
