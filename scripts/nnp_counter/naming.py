"""กติกาตั้งชื่อ: ปี-เดือน, ชื่อไฟล์, ชื่อ label, Gmail query"""
from __future__ import annotations

import datetime as dt
import re

from .config import TZ, NnpError, OrgConfig

YM_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
TEST_LABEL_PREFIX = "zz-test-"


def validate_ym(value) -> str:
    s = str(value).strip()
    if not YM_RE.match(s):
        raise NnpError(f"รูปแบบปี-เดือนไม่ถูกต้อง: {s!r} (ต้องเป็น YYYY-MM เช่น 2026-09)")
    return s


def shift_ym(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    idx = y * 12 + (m - 1) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def current_ym() -> str:
    return dt.datetime.now(TZ).strftime("%Y-%m")


def month_bounds_epoch(ym: str) -> tuple[int, int]:
    """[ต้นเดือน, ต้นเดือนถัดไป) เป็น epoch วินาที ตามเวลา Asia/Bangkok"""
    a = dt.datetime(int(ym[:4]), int(ym[5:7]), 1, tzinfo=TZ)
    nxt = shift_ym(ym, 1)
    b = dt.datetime(int(nxt[:4]), int(nxt[5:7]), 1, tzinfo=TZ)
    return int(a.timestamp()), int(b.timestamp())


def report_name(cfg: OrgConfig, ym: str) -> str:
    return f"{cfg.prefix}-{ym}.xlsx"


def history_name(cfg: OrgConfig, ym: str) -> str:
    return f"{cfg.prefix}-flow-history-{ym}.xlsx"


def label_name(cfg: OrgConfig, ym: str, env: str = "prod") -> str:
    prefix = (TEST_LABEL_PREFIX if env == "test" else "") + cfg.prefix
    return f"{prefix}-{ym}"


def gmail_query(cfg: OrgConfig, ym: str) -> str:
    a, b = month_bounds_epoch(ym)
    return f"from:{cfg.sender} after:{a} before:{b}"


def classify(cfg: OrgConfig, filename: str):
    """คืน (kind, ym) โดย kind = master | report | history | None"""
    if filename == cfg.master_file:
        return "master", None
    m = re.match(rf"^{re.escape(cfg.prefix)}-flow-history-(\d{{4}}-\d{{2}})\.xlsx$", filename)
    if m and YM_RE.match(m.group(1)):
        return "history", m.group(1)
    m = re.match(rf"^{re.escape(cfg.prefix)}-(\d{{4}}-\d{{2}})\.xlsx$", filename)
    if m and YM_RE.match(m.group(1)):
        return "report", m.group(1)
    return None, None
