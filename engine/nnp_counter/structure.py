"""โครงสร้างโฟลเดอร์, สร้างไฟล์รายเดือน, ย้ายไฟล์ที่อยู่ผิดที่, สำรองไฟล์, sandbox สำหรับ dry-run"""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

from . import naming
from .config import HISTORY_COLUMNS, REPORT_COLUMNS, TZ
from .context import Ctx
from .xlsxio import new_workbook


def ensure_dirs(ctx: Ctx) -> list[str]:
    made = []
    for kind in ("master", "history", "report"):
        d = ctx.dir(kind)
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            made.append(str(d))
    return made


def move_misplaced(ctx: Ctx) -> dict:
    """ย้ายไฟล์ report/history/master ที่อยู่ผิดโฟลเดอร์เข้าที่ที่ถูก (ไม่เขียนทับ ไม่ลบ)"""
    moved, conflicts = [], []
    locations = [ctx.data_root] + [ctx.dir(k) for k in ("master", "history", "report")]
    for loc in locations:
        if not loc.exists():
            continue
        for f in sorted(loc.glob("*.xlsx")):
            if f.name.startswith("~$"):
                continue
            kind, _ = naming.classify(ctx.cfg, f.name)
            if not kind:
                continue
            target = ctx.dir(kind) / f.name
            if f.parent == target.parent:
                continue
            if target.exists():
                conflicts.append({"file": str(f), "target": str(target)})
                continue
            shutil.move(str(f), str(target))
            moved.append({"from": str(f), "to": str(target)})
    return {"moved": moved, "conflicts": conflicts}


def ensure_month_files(ctx: Ctx) -> list[str]:
    created = []
    for path, cols in ((ctx.report_path, REPORT_COLUMNS), (ctx.history_path, HISTORY_COLUMNS)):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            new_workbook(cols).save(path)
            created.append(str(path))
    return created


def backup(ctx: Ctx, tag: str = "") -> str | None:
    """สำรองไฟล์ที่กำลังจะถูกเขียนไว้ใน _work/backup/ (ข้ามถ้า dry-run)"""
    if ctx.dry_run:
        return None
    stamp = dt.datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    dest = ctx.root / "_work" / "backup" / f"{stamp}-{ctx.org}-{ctx.ym}{tag}"
    n = 0
    for p in (ctx.report_path, ctx.history_path):
        if p.exists():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest / p.name)
            n += 1
    return str(dest) if n else None


def make_sandbox(root: Path, org: str, ym: str) -> Path:
    stamp = dt.datetime.now(TZ).strftime("%H%M%S")
    sb = Path(root) / "_work" / "dryrun" / f"{org}-{ym}-{stamp}"
    sb.mkdir(parents=True, exist_ok=True)
    return sb


def seed_sandbox(real: Ctx, sandbox_ctx: Ctx, ignore_existing: bool = False) -> list[str]:
    """คัดลอกไฟล์จริงที่จำเป็น (master, report เดือนก่อน/เดือนนี้, history เดือนนี้) ไปไว้ใน sandbox
    ignore_existing=True: ไม่คัดลอก report/history ของเดือนนี้ (เริ่มจากไฟล์ว่าง ใช้เทียบผลกับของเดิม)"""
    copied = []
    pairs = [(real.master_path, sandbox_ctx.master_path), (real.prev_report_path, sandbox_ctx.prev_report_path)]
    if not ignore_existing:
        pairs += [(real.report_path, sandbox_ctx.report_path), (real.history_path, sandbox_ctx.history_path)]
    for src, dst in pairs:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(src.name)
    return copied
