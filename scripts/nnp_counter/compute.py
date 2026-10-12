"""กติกาธุรกิจ: สถานะอีเมล, previousMonth/diff, SUPERSEDED, ธงแดง (เหมือน flow เดิมทุกประการ)"""
from __future__ import annotations

import re

from . import emailparse as ep
from .config import DONE_PATTERN, OrgConfig

DONE_RE = re.compile(DONE_PATTERN)


def key(v) -> str:
    return (ep.clean(v) or "").upper()


def compute(cfg: OrgConfig, ym: str, metas: list[dict], bodies: dict, master: list[dict],
            prev_rows: list[dict], prev_file_exists: bool, main_rows: list[dict],
            history_status: dict, stamp: str, reprocess: bool = False) -> dict:
    """
    metas: [{id, threadId, sender, internalDate, text}]  (text = snippet หรือ excerpt)
    bodies: {id: (color, pct) | None}  ผล parse_toner ของอีเมลเนื้อเต็ม
    history_status: {id: status}
    """
    master_map = {key(m["machine"]): m for m in master}
    prev_map = {key(r.get("serialNumber")): r for r in prev_rows if key(r.get("serialNumber"))}
    main_map = {key(r.get("serialNumber")): r for r in main_rows if key(r.get("serialNumber"))}
    prev_usable = prev_file_exists and len(prev_map) > 0
    notes, infos = [], []
    if not prev_usable:
        if cfg.prev_file_missing == "blank":
            notes.append("previous month file missing or empty: previousMonth and diff left blank")
        else:
            infos.append("previous month file missing or empty: previousMonth treated as 0 (rows not flagged)")

    cand, seen = [], set()
    for m in metas:
        mid = m.get("id")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        if not reprocess and DONE_RE.match(history_status.get(mid, "")):
            continue
        cand.append(m)

    results = []
    for m in cand:
        base = {"id": m["id"], "threadId": m.get("threadId") or "", "serial": ""}
        sender = (m.get("sender") or "").lower()
        if sender and cfg.sender.lower() not in sender:
            results.append({**base, "status": "ERROR_BAD_SENDER"})
            continue
        f = ep.parse_fields(m.get("text", ""))
        serial = (ep.clean(f["serialNumber"]) or "").split(" ")[0]
        base["serial"] = serial
        if not serial:
            results.append({**base, "status": "ERROR_NO_SERIAL"})
            continue
        ms = ep.parse_date(ep.clean(f["machineDate"]))
        if ms is None:
            results.append({**base, "status": "ERROR_PARSE_DATE"})
            continue
        email_date = ep.fmt_date(ms)
        if ep.ym_of(ms) != ym:
            results.append({**base, "status": "SKIPPED_OTHER_MONTH", "emailDate": email_date})
            continue
        mst = master_map.get(serial.upper())
        if not mst:
            results.append({**base, "status": "ERROR_NO_MASTER", "emailDate": email_date})
            continue
        total = int(ep.clean(f["totalCounter"]) or 0)
        prev_total: int | str = ""
        diff: int | str = ""
        flag = False
        if prev_usable:
            pr = prev_map.get(serial.upper())
            if pr:
                prev_total = int(pr.get("totalCounter") or 0)
            else:
                prev_total = 0
                flag = cfg.flag_new_machines
            diff = total - prev_total
        elif cfg.prev_file_missing == "zero":
            prev_total, diff = 0, total
        results.append({**base, "status": "COMPLETE", "emailDate": email_date, "ms": ms, "flag": flag,
                        "model": ep.clean(f["machineModel"]),
                        "row": {"machineDate": email_date, "serialNumber": serial,
                                "machineModel": ep.clean(f["machineModel"]), "unit": ep.clean(mst["unit"]),
                                "building": ep.clean(mst["building"]), "previousMonth": prev_total,
                                "totalCounter": total, "diff": diff, "remaining": ""}})

    # SUPERSEDED: ฉบับที่ใหม่สุดต่อเครื่อง + ไม่เก่ากว่าแถวที่มีอยู่แล้ว
    best: dict[str, int] = {}
    for i, r in enumerate(results):
        if r["status"] != "COMPLETE":
            continue
        cur = best.get(r["serial"].upper())
        if cur is None or r["ms"] > results[cur]["ms"]:
            best[r["serial"].upper()] = i
    for i, r in enumerate(results):
        if r["status"] != "COMPLETE":
            continue
        if best.get(r["serial"].upper()) != i:
            r["status"] = "SUPERSEDED"
            continue
        ex = main_map.get(r["serial"].upper())
        ex_ms = ep.parse_date(ex.get("machineDate")) if ex and isinstance(ex.get("machineDate"), str) else None
        if not reprocess and ex_ms is not None and ex_ms > r["ms"]:
            r["status"] = "SUPERSEDED"

    need_body, main_out = [], []
    for r in results:
        if r["status"] != "COMPLETE":
            continue
        if r["id"] in bodies:
            t = bodies[r["id"]]
            r["row"]["remaining"] = int(t[1]) / 100 if t else ""
        else:
            need_body.append(r["id"])
        main_out.append(r["row"])
        if r["row"]["diff"] != "" and r["row"]["diff"] < 0:
            notes.append(f"machine {r['serial']} has negative diff ({r['row']['diff']}): check totalCounter")
    flagged = [r["serial"] for r in results if r["status"] == "COMPLETE" and r.get("flag")]
    for s in flagged:
        notes.append(f"machine {s} is not in the previous month file: row highlighted red")

    history_out = [{"Id": r["id"], "ThreadId": r["threadId"], "SerialNumber": r["serial"],
                    "Status": r["status"], "Timestamp": stamp} for r in results]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    issues = [{"id": r["id"], "serial": r["serial"], "status": r["status"]} for r in results
              if re.match(r"^(ERROR|SKIPPED)", r["status"])]
    return {"results": results, "main_rows": main_out, "history_rows": history_out, "flagged": flagged,
            "notes": notes, "infos": infos, "counts": counts, "issues": issues, "need_body": need_body,
            "label_ids": [r["id"] for r in results if r["status"] in ("COMPLETE", "SUPERSEDED")],
            "prev_usable": prev_usable, "candidates": len(cand)}
