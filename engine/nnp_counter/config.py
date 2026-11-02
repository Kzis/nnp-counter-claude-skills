"""ค่าคงที่ + โหลด config ของแต่ละองค์กรจาก nnp-config.json ในโฟลเดอร์ข้อมูลของผู้ใช้"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=7))  # Asia/Bangkok
CONFIG_NAME = "nnp-config.json"
ORG_RE = re.compile(r"^[a-z][a-z0-9-]{1,19}$")

REPORT_COLUMNS = ["machineDate", "serialNumber", "machineModel", "unit", "building",
                  "previousMonth", "totalCounter", "diff", "remaining"]
HISTORY_COLUMNS = ["Id", "ThreadId", "SerialNumber", "Status", "Timestamp"]
MISSING_HEADER = ["unit", "machine", "building", "reportedLastMonth"]
DONE_PATTERN = r"^(COMPLETE|SKIPPED|SUPERSEDED)"
ALLOWED_GMAIL_TOOLS = ("search_threads", "get_thread", "get_message", "list_labels",
                       "create_label", "label_message")

DEFAULT_DIRS = {"master": "01_master", "history": "02_historys", "report": "03_report_files"}
DEFAULT_MASTER_COLUMNS = {"unit": "unit", "machine": "machine", "building": "building"}


class NnpError(Exception):
    """ข้อผิดพลาดที่ผู้ใช้ต้องแก้/รับทราบ (ไม่ใช่ bug)"""


@dataclass
class OrgConfig:
    org: str
    display_name: str
    data_dir: str
    sender: str
    dirs: dict = field(default_factory=lambda: dict(DEFAULT_DIRS))
    master_file: str = ""
    master_sheet: str | None = None
    master_columns: dict = field(default_factory=lambda: dict(DEFAULT_MASTER_COLUMNS))
    prefix: str = ""
    flag_new_machines: bool = False
    flag_color: str = "FF6666"
    prev_file_missing: str = "blank"  # zero | blank

    def __post_init__(self):
        self.prefix = self.prefix or self.org
        self.master_file = self.master_file or f"master_{self.org}.xlsx"


def find_root(start: Path | str | None = None) -> Path | None:
    """หาโฟลเดอร์ข้อมูล = โฟลเดอร์แรก (ไล่ขึ้นข้างบน) ที่มี nnp-config.json"""
    p = Path(start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / CONFIG_NAME).exists():
            return d
    return None


def config_path(root: Path | str) -> Path:
    return Path(root) / CONFIG_NAME


def read_config(root: Path | str) -> dict:
    path = config_path(root)
    if not path.exists():
        raise NnpError(f"ไม่พบ {CONFIG_NAME} ใน {root} — รัน `init` หรือ /nnp-counter:setup ก่อน")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise NnpError(f"{path} อ่านไม่ได้ (JSON ผิดรูปแบบ): {e}")
    data.setdefault("orgs", {})
    return data


def write_config(root: Path | str, data: dict) -> None:
    config_path(root).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_orgs(root: Path | str) -> list[str]:
    return sorted(read_config(root)["orgs"])


def validate_org_name(org: str) -> str:
    if not ORG_RE.match(org or ""):
        raise NnpError(f"ชื่อ org ไม่ถูกต้อง: {org!r} (ใช้ a-z 0-9 และ - ยาว 2–20 ตัว ขึ้นต้นด้วยตัวอักษร เช่น oag, mwd)")
    return org


def load_org(org: str, root: Path | str) -> OrgConfig:
    data = read_config(root)
    orgs = data["orgs"]
    if org not in orgs:
        known = ", ".join(sorted(orgs)) or "(ยังไม่มี)"
        raise NnpError(f"ไม่รู้จัก org {org!r} — org ที่ตั้งไว้: {known} (เพิ่มด้วย add-org / /nnp-counter:add-org)")
    raw = dict(orgs[org])
    raw["org"] = org
    try:
        cfg = OrgConfig(**raw)
    except TypeError as e:
        raise NnpError(f"config ของ {org} มีฟิลด์ไม่ถูกต้อง/ขาด: {e}")
    if not cfg.sender or "@" not in cfg.sender:
        raise NnpError(f"config ของ {org}: sender ต้องเป็นอีเมลของผู้ส่งรายงาน (ตอนนี้: {cfg.sender!r})")
    if cfg.prev_file_missing not in ("zero", "blank"):
        raise NnpError("prev_file_missing ต้องเป็น zero หรือ blank")
    for k in ("master", "history", "report"):
        if k not in cfg.dirs:
            raise NnpError(f"config ของ {org}: dirs ขาด {k}")
    for k in ("unit", "machine", "building"):
        if k not in cfg.master_columns:
            raise NnpError(f"config ของ {org}: master_columns ขาด {k}")
    return cfg
