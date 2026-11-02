"""แกะข้อมูลจากอีเมลรายงานเครื่องถ่ายเอกสาร (snippet หรือเนื้อเต็ม) — logic ตรงกับ flow เดิม"""
from __future__ import annotations

import datetime as dt
import re

_DATE_VAL = r"(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?|\d{2}-\d{2}-\d{4}(?:[ T]\d{2}:\d{2})?)"


def clean(v) -> str | None:
    if v is None:
        return None
    return re.sub(r"\s+", " ", str(v)).strip()


def parse_fields(text: str) -> dict:
    """ใช้ได้ทั้ง snippet (บรรทัดเดียว) และเนื้อเต็ม (หลายบรรทัด/มี tab)"""
    t = re.sub(r"\s+", " ", (text or "").replace("\r", " "))

    def pick(rx):
        m = re.search(rx, t)
        return m.group(1).strip() if m else None

    return {
        "machineDate": pick(r"(?<![A-Za-z])Date\s*:\s*" + _DATE_VAL),
        "machineModel": pick(r"Machine Model\s*:\s*(.+?)\s+Serial Number\s*:"),
        "serialNumber": pick(r"Serial Number\s*:\s*(\S+)"),
        "totalCounter": pick(r"Total Counter\s*:\s*(\d+)"),
    }


def parse_toner(text: str | None) -> tuple[str, str] | None:
    """คืน (สี, เปอร์เซ็นต์) ของสีแรกที่พบหลังคำว่า 'Toner Information' (ถ้าไม่มีคำนี้ใช้ทั้งข้อความ)"""
    if not text:
        return None
    t = re.sub(r"\s+", " ", text)
    i = t.find("Toner Information")
    blk = t[i + len("Toner Information"):] if i != -1 else t
    m = re.search(r"(Black|Cyan|Magenta|Yellow)\s+(\d+)", blk)
    return (m.group(1), m.group(2)) if m else None


def parse_date(raw) -> int | None:
    """คืน ms (UTC ตามตัวเลขที่เขียนในอีเมล ไม่แปลง timezone) หรือ None"""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return round((raw - 25569) * 86400000)
    s = str(raw).strip().lstrip("'")
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?", s)
    if m:
        return _utc_ms(int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0), int(m[5] or 0))
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})(?:[ T](\d{2}):(\d{2}))?", s)
    if m:
        day, month = int(m[1]), int(m[2])
        if month > 12 and day <= 12:
            day, month = month, day
        return _utc_ms(int(m[3]), month, day, int(m[4] or 0), int(m[5] or 0))
    if re.match(r"^\d+(\.\d+)?$", s):
        return round((float(s) - 25569) * 86400000)
    return None


def _utc_ms(y, mo, d, h, mi) -> int | None:
    try:
        return int(dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc).timestamp() * 1000)
    except ValueError:
        return None


def fmt_date(ms: int) -> str:
    d = dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc)
    return d.strftime("%d-%m-%Y %H:%M")


def ym_of(ms: int) -> str:
    d = dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc)
    return d.strftime("%Y-%m")
