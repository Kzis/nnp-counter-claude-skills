"""ตรวจความถูกต้องของไฟล์ผลลัพธ์หลัง apply"""
from __future__ import annotations

import re

from . import emailparse as ep
from . import xlsxio
from .config import HISTORY_COLUMNS, REPORT_COLUMNS, NnpError
from .context import Ctx

VALID_STATUS = re.compile(r"^(COMPLETE|SUPERSEDED|SKIPPED_OTHER_MONTH|ERROR_[A-Z_]+)$")


def verify(ctx: Ctx) -> dict:
    checks, warnings = [], []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    try:
        rows = xlsxio.read_rows(ctx.report_path, "Sheet1", REPORT_COLUMNS)
        check("report header", True)
    except NnpError as e:
        check("report header", False, str(e))
        return {"ok": False, "checks": checks, "warnings": warnings}
    try:
        hist = xlsxio.read_rows(ctx.history_path, "Sheet1", HISTORY_COLUMNS)
        check("history header", True)
    except NnpError as e:
        check("history header", False, str(e))
        return {"ok": False, "checks": checks, "warnings": warnings}

    master = xlsxio.read_master(ctx.master_path, ctx.cfg)
    master_keys = {m["machine"].upper() for m in master}

    wrong_month = [r["serialNumber"] for r in rows if ep.ym_of(ep.parse_date(r["machineDate"]) or 0) != ctx.ym]
    check("ทุกแถวอยู่ในเดือน " + ctx.ym, not wrong_month, f"ผิดเดือน: {wrong_month[:5]}")
    not_in_master = [r["serialNumber"] for r in rows if str(r["serialNumber"]).upper() not in master_keys]
    check("ทุก serial อยู่ใน master", not not_in_master, f"ไม่อยู่ใน master: {not_in_master[:5]}")
    serials = [str(r["serialNumber"]).upper() for r in rows]
    dup = sorted({s for s in serials if serials.count(s) > 1})
    check("ไม่มี serial ซ้ำ", not dup, f"ซ้ำ: {dup[:5]}")
    bad_diff = [r["serialNumber"] for r in rows
                if r.get("previousMonth") not in (None, "") and r.get("diff") not in (None, "")
                and r["diff"] != r["totalCounter"] - r["previousMonth"]]
    check("diff = totalCounter − previousMonth", not bad_diff, f"ผิด: {bad_diff[:5]}")
    neg = [r["serialNumber"] for r in rows if isinstance(r.get("diff"), (int, float)) and r["diff"] < 0]
    if neg:
        warnings.append(f"diff ติดลบ (ตรวจ totalCounter): {neg[:5]}")

    ids = [h["Id"] for h in hist]
    check("history ไม่มี Id ซ้ำ", len(ids) == len(set(ids)))
    bad_status = sorted({h["Status"] for h in hist if not VALID_STATUS.match(str(h["Status"]))})
    check("history สถานะถูกต้อง", not bad_status, f"แปลก: {bad_status}")
    complete_serials = {str(h["SerialNumber"]).upper() for h in hist if h["Status"] == "COMPLETE"}
    missing_rows = sorted(complete_serials - set(serials))
    check("ทุก COMPLETE ใน history มีแถวในรายงาน", not missing_rows, f"ไม่มีแถว: {missing_rows[:5]}")
    errs = [h for h in hist if str(h["Status"]).startswith("ERROR")]
    if errs:
        warnings.append(f"มีอีเมลสถานะ ERROR {len(errs)} ฉบับ (จะถูกลองใหม่รอบหน้า): "
                        + ", ".join(sorted({f"{h['SerialNumber']}:{h['Status']}" for h in errs})[:8]))

    ms = xlsxio.read_missing_summary(ctx.report_path)
    if ms is None:
        check("มีแท็บ missing", False, "ไม่พบแท็บ missing")
    else:
        in_master_sent = len({s for s in serials if s in master_keys})
        check("missing: ส่งแล้ว + ยังไม่ส่ง = ทั้งหมด", ms["sent"] + ms["missing"] == ms["total"],
              f"{ms['sent']}+{ms['missing']} vs {ms['total']}")
        check("missing: จำนวนส่งแล้ว = แถวใน Sheet1 ที่อยู่ใน master", ms["sent"] == in_master_sent,
              f"{ms['sent']} vs {in_master_sent}")
        check("missing: จำนวนแถวตาราง = ยังไม่ส่ง", ms["table_rows"] == ms["missing"],
              f"{ms['table_rows']} vs {ms['missing']}")
    return {"ok": all(c["ok"] for c in checks), "checks": checks, "warnings": warnings,
            "rows": len(rows), "history_rows": len(hist), "missing": ms}
