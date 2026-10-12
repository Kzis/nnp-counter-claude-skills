"""ค่าคงที่ + โหลด config ของแต่ละ org"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TZ = dt.timezone(dt.timedelta(hours=7))  # Asia/Bangkok
ORGS = ("oag", "mwd")

REPORT_COLUMNS = ["machineDate", "serialNumber", "machineModel", "unit", "building",
                  "previousMonth", "totalCounter", "diff", "remaining"]
HISTORY_COLUMNS = ["Id", "ThreadId", "SerialNumber", "Status", "Timestamp"]
MISSING_HEADER = ["unit", "machine", "building", "reportedLastMonth"]
DONE_PATTERN = r"^(COMPLETE|SKIPPED|SUPERSEDED)"
ALLOWED_GMAIL_TOOLS = ("search_threads", "get_thread", "get_message", "list_labels",
                       "create_label", "label_message", "label_thread")


class NnpError(Exception):
    """ข้อผิดพลาดที่ผู้ใช้ต้องแก้/รับทราบ (ไม่ใช่ bug)"""


@dataclass
class OrgConfig:
    org: str
    display_name: str
    data_dir: str
    dirs: dict
    master_file: str
    master_sheet: str | None
    master_columns: dict
    sender: str
    prefix: str
    flag_new_machines: bool
    flag_color: str
    prev_file_missing: str  # zero | blank


def load_org(org: str, root: Path | str = REPO_ROOT) -> OrgConfig:
    if org not in ORGS:
        raise NnpError(f"org ไม่ถูกต้อง: {org!r} (ต้องเป็น {' หรือ '.join(ORGS)})")
    path = Path(root) / "agents" / org / "config.yaml"
    if not path.exists():
        raise NnpError(f"ไม่พบ config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg = OrgConfig(**data)
    if cfg.org != org:
        raise NnpError(f"config {path} ระบุ org={cfg.org} ไม่ตรงกับ {org}")
    if cfg.prev_file_missing not in ("zero", "blank"):
        raise NnpError("prev_file_missing ต้องเป็น zero หรือ blank")
    return cfg
