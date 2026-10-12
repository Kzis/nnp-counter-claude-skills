import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from nnp_counter.config import REPORT_COLUMNS  # noqa: E402


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


@pytest.fixture()
def repo(tmp_path):
    """โครง repo จำลองใน tmp: config จริง + master เล็กๆ"""
    for org in ("oag", "mwd"):
        (tmp_path / "agents" / org).mkdir(parents=True)
        shutil.copy(REPO / "agents" / org / "config.yaml", tmp_path / "agents" / org / "config.yaml")
    make_master(tmp_path / "02_สตง/01_master/master_oag.xlsx",
                [("สตง.", "AAA111", "อาคาร 1"), ("สตง.", "BBB222", "อาคาร 2"), ("สตง.", "CCC333", "อาคาร 3")])
    make_master(tmp_path / "01_ประปา/01_master/master_mwd.xlsx",
                [("ฝ่าย ก", "bldg ก", "XXX111", 0, 1, 1), ("ฝ่าย ข", "bldg ข", "YYY222", 0, 1, 1)],
                sheet="master", header=("unit", "building", "machine", "start", "current", "count"))
    return tmp_path


def snippet(date, serial, total, model="TOSHIBA e-STUDIO4528A"):
    return (f"Date : {date} Machine Model : {model} Serial Number : {serial} Total Counter : {total} "
            "Supplier: Name : Tel Number : E-Mail : Address : Customer: Name : Tel Number :")


def run_cli(repo, *args, stdin=""):
    p = subprocess.run([sys.executable, str(REPO / "scripts" / "nnp_cli.py"), "--root", str(repo), *args],
                       input=stdin, capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout ไม่ใช่ JSON: {p.stdout!r} stderr={p.stderr!r}")
    return p.returncode, data


def jl(*rows):
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
