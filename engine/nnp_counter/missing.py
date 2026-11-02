"""คำนวณแท็บ missing: เครื่องใน master ที่ยังไม่มีแถวใน Sheet1 ของเดือนนี้"""
from __future__ import annotations

from . import emailparse as ep


def _k(v) -> str:
    return (ep.clean(v) or "").upper()


def compute_missing(master: list[dict], sent_rows: list[dict], prev_rows: list[dict],
                    prev_file_exists: bool, stamp: str) -> dict:
    sent = {_k(r.get("serialNumber")) for r in sent_rows if _k(r.get("serialNumber"))}
    prev_sent = {_k(r.get("serialNumber")) for r in prev_rows if _k(r.get("serialNumber"))}
    prev_usable = prev_file_exists and len(prev_sent) > 0
    seen, dups, missing = set(), [], []
    total = sent_count = 0
    for m in master:
        k = _k(m["machine"])
        if not k:
            continue
        if k in seen:
            dups.append(k)
            continue
        seen.add(k)
        total += 1
        if k in sent:
            sent_count += 1
            continue
        reported = ("ใช่" if k in prev_sent else "ไม่") if prev_usable else ""
        missing.append([ep.clean(m["unit"]) or "", ep.clean(m["machine"]) or "", ep.clean(m["building"]) or "", reported])
    table = [["unit", "machine", "building", "reportedLastMonth"]] + missing
    summary = [["เครื่องใน master (ทั้งหมด)", total], ["ส่งข้อมูลแล้ว", sent_count],
               ["ยังไม่ส่งข้อมูล", len(missing)], ["อัปเดตล่าสุด", stamp]]
    return {"table": table, "summary": summary, "total": total, "sent": sent_count,
            "missing": len(missing), "dup_serials": dups, "prev_usable": prev_usable}
