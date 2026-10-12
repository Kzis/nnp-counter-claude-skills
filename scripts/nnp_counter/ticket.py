"""ใบสั่งงาน (ticket) + state machine บังคับลำดับขั้น + lock กันรันซ้อน"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .config import TZ, NnpError

STATES = ["begun", "collecting", "planned", "applied", "labeled", "verified"]
STALE_HOURS = 3


def now_iso() -> str:
    return dt.datetime.now(TZ).isoformat(timespec="seconds")


def load(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise NnpError(f"ยังไม่มีใบสั่งงาน ({path.name}) — ต้องรัน begin ก่อนเสมอ")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, t: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    t["updated"] = now_iso()
    path.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


def check_can_begin(path: Path, dry_run: bool, force: bool) -> None:
    """ปฏิเสธถ้ามีงานจริงของ org+เดือนเดียวกันค้างอยู่ (ยังไม่ verified และยังไม่ stale)"""
    path = Path(path)
    if not path.exists() or force:
        return
    t = json.loads(path.read_text(encoding="utf-8"))
    if t.get("state") == "verified":
        return
    age = dt.datetime.now(TZ) - dt.datetime.fromisoformat(t.get("updated", t["created"]))
    if t.get("state") == "aborted":
        return
    if age < dt.timedelta(hours=STALE_HOURS) and not (t.get("dry_run") and dry_run):
        raise NnpError(f"มีงานของ {t['org']} {t['ym']} ค้างอยู่ที่ขั้น '{t['state']}' (อัปเดต {t['updated']}) "
                       f"— ทำต่อให้จบ หรือใช้ --force ถ้าแน่ใจว่าไม่มีใครรันอยู่")


def abort(path: Path) -> dict:
    """ยกเลิกใบสั่งงานที่ค้าง (ให้ Stop hook ไม่บล็อก และ begin ใหม่ได้)"""
    t = load(path)
    t["state_before_abort"] = t["state"]
    t["state"] = "aborted"
    save(path, t)
    return t


def require(t: dict, at_least: str, command: str) -> None:
    if t["state"] not in STATES:
        raise NnpError(f"ใบสั่งงานอยู่สถานะ '{t['state']}' — เริ่มใหม่ด้วย begin")
    if STATES.index(t["state"]) < STATES.index(at_least):
        raise NnpError(f"คำสั่ง {command} ต้องทำหลังขั้น '{at_least}' แต่ตอนนี้อยู่ที่ขั้น '{t['state']}' "
                       f"— ทำตามลำดับ: {' → '.join(STATES)}")


def advance(t: dict, to: str) -> None:
    """เลื่อนสถานะไปข้างหน้าเท่านั้น (ถ้าอยู่ไกลกว่าแล้วไม่ถอยหลัง)"""
    if t["state"] in STATES and STATES.index(to) > STATES.index(t["state"]):
        t["state"] = to
