"""ตัวช่วยร่วมของ hooks (ไม่พึ่งไลบรารีนอก stdlib)"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / ".run"
TZ = dt.timezone(dt.timedelta(hours=7))
STALE = dt.timedelta(hours=3)
LABEL_RE = re.compile(r"^(zz-test-)?(oag|mwd)-\d{4}-(0[1-9]|1[0-2])$")
DATA_SUBDIRS = ("01_master", "02_historys", "03_report_files")
READ_TOOLS = {"search_threads", "get_thread", "get_message", "list_labels"}


def read_input() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def block(msg: str) -> None:
    print(f"[nnp-guard] {msg}", file=sys.stderr)
    sys.exit(2)


def heartbeat(event: str) -> None:
    try:
        RUN.mkdir(exist_ok=True)
        (RUN / "hook-heartbeat").write_text(
            json.dumps({"at": dt.datetime.now(TZ).isoformat(timespec="seconds"), "event": event}), encoding="utf-8")
    except Exception:
        pass


def tickets(active_only: bool = True) -> list[dict]:
    out = []
    for p in sorted(RUN.glob("*-*.json")) if RUN.exists() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "org" not in t or "ym" not in t:
            continue
        if active_only:
            if t.get("state") in ("verified", "aborted"):
                continue
            age = dt.datetime.now(TZ) - dt.datetime.fromisoformat(t.get("updated", t["created"]))
            if age > STALE:
                continue
        out.append(t)
    return out


def data_dirs() -> list[str]:
    names = []
    for cfg in (ROOT / "agents").glob("*/config.yaml"):
        m = re.search(r'^data_dir:\s*"?([^"\s#]+)', cfg.read_text(encoding="utf-8"), re.M)
        if m:
            names.append(m.group(1))
    return names or ["01_ประปา", "02_สตง"]
