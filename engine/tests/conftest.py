import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent
sys.path.insert(0, str(ENGINE))

OAG_SENDER = "reports@oag.example"
MWD_SENDER = "reports@mwd.example"
TEST_CONFIG = {"version": 1, "orgs": {
    "oag": {"display_name": "Org A (oag)", "data_dir": "data-oag", "sender": OAG_SENDER,
            "master_file": "master_oag.xlsx", "master_sheet": None,
            "master_columns": {"unit": "unit", "machine": "machine", "building": "building"},
            "prefix": "oag", "flag_new_machines": True, "flag_color": "FF6666", "prev_file_missing": "zero"},
    "mwd": {"display_name": "Org B (mwd)", "data_dir": "data-mwd", "sender": MWD_SENDER,
            "master_file": "master_mwd.xlsx", "master_sheet": "master",
            "master_columns": {"unit": "unit", "machine": "machine", "building": "building"},
            "prefix": "mwd", "flag_new_machines": False, "flag_color": "FF6666", "prev_file_missing": "blank"}}}

from nnp_counter.config import REPORT_COLUMNS, load_org  # noqa: E402


def make_master(path: Path, rows, sheet=None, header=("unit", "machine", "building")):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet or "Sheet1"
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    wb.save(path)


def make_report(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(REPORT_COLUMNS)
    for r in rows:
        ws.append([r.get(c, "") for c in REPORT_COLUMNS])
    wb.save(path)


def write_config(root: Path):
    (root / "nnp-config.json").write_text(json.dumps(TEST_CONFIG, ensure_ascii=False), encoding="utf-8")


_cfg_root = []


def load_test_org(org: str):
    if not _cfg_root:
        import tempfile
        d = Path(tempfile.mkdtemp())
        write_config(d)
        _cfg_root.append(d)
    return load_org(org, _cfg_root[0])


@pytest.fixture()
def repo(tmp_path):
    """โฟลเดอร์ข้อมูลจำลองใน tmp: nnp-config.json + master เล็กๆ ของ 2 องค์กร"""
    write_config(tmp_path)
    make_master(tmp_path / "data-oag/01_master/master_oag.xlsx",
                [("หน่วยงาน A", "AAA111", "อาคาร 1"), ("หน่วยงาน A", "BBB222", "อาคาร 2"), ("หน่วยงาน A", "CCC333", "อาคาร 3")])
    make_master(tmp_path / "data-mwd/01_master/master_mwd.xlsx",
                [("ฝ่าย ก", "XXX111", "bldg ก"), ("ฝ่าย ข", "YYY222", "bldg ข")], sheet="master")
    return tmp_path


def snippet(date, serial, total, model="TOSHIBA e-STUDIO4528A"):
    return (f"Date : {date} Machine Model : {model} Serial Number : {serial} Total Counter : {total} "
            "Supplier: Name : Tel Number : E-Mail : Address : Customer: Name : Tel Number :")


def run_cli(repo, *args, stdin=""):
    import os
    env = dict(os.environ, PYTHONPATH=str(ENGINE), PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "nnp_counter", "--root", str(repo), *args],
                       input=stdin, capture_output=True, text=True, env=env)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout ไม่ใช่ JSON: {p.stdout!r} stderr={p.stderr!r}")
    return p.returncode, data


def jl(*rows):
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
