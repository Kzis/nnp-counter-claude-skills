import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO, run_cli

Q = "from:networkservice@oag.go.th after:1788195600 before:1790787600"


@pytest.fixture()
def hrepo(repo):
    shutil.copytree(REPO / "hooks", repo / "hooks", ignore=shutil.ignore_patterns("__pycache__"))
    return repo


def hook(hrepo, name, payload):
    p = subprocess.run([sys.executable, str(hrepo / "hooks" / name)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(hrepo))
    return p.returncode, p.stdout, p.stderr


def gm(tool, **args):
    return {"tool_name": f"mcp__Gmail__{tool}", "tool_input": args}


def begin(hrepo, *extra):
    return run_cli(hrepo, "begin", "--org", "oag", "--month", "2026-09", *extra)


def test_gmail_search_requires_ticket_and_exact_query(hrepo):
    assert hook(hrepo, "guard_gmail.py", gm("search_threads", query=Q))[0] == 2           # ไม่มี ticket
    begin(hrepo)
    assert hook(hrepo, "guard_gmail.py", gm("search_threads", query=Q))[0] == 0
    assert hook(hrepo, "guard_gmail.py", gm("search_threads", query=Q + " OR from:x"))[0] == 2
    assert hook(hrepo, "guard_gmail.py", gm("search_threads", query="from:networkservice@oag.go.th"))[0] == 2


def test_gmail_dangerous_tools_always_blocked(hrepo):
    begin(hrepo)
    for t in ("send_message", "trash_message", "reply", "forward", "delete_label", "label_thread", "create_draft"):
        assert hook(hrepo, "guard_gmail.py", gm(t))[0] == 2, t
    for t in ("list_labels", "get_message", "get_thread"):
        assert hook(hrepo, "guard_gmail.py", gm(t))[0] == 0, t


def test_label_writes_need_real_applied_ticket(hrepo):
    begin(hrepo, "--dry-run")
    assert hook(hrepo, "guard_gmail.py", gm("label_message", messageId="m", labelIds=["L"]))[0] == 2
    assert hook(hrepo, "guard_gmail.py", gm("create_label", name="oag-2026-09"))[0] == 2   # dry-run
    run_cli(hrepo, "abort", "--org", "oag", "--month", "2026-09")
    begin(hrepo)
    assert hook(hrepo, "guard_gmail.py", gm("create_label", name="oag-2026-09"))[0] == 0
    assert hook(hrepo, "guard_gmail.py", gm("create_label", name="oag-2026-10"))[0] == 2   # ไม่ตรง ticket
    assert hook(hrepo, "guard_gmail.py", gm("create_label", name="random"))[0] == 2
    assert hook(hrepo, "guard_gmail.py", gm("label_message", messageId="m", labelIds=["L"]))[0] == 2  # ยังไม่ apply


def test_file_guard(hrepo):
    f = lambda tool, **a: hook(hrepo, "guard_files.py", {"tool_name": tool, "tool_input": a})[0]
    assert f("Write", file_path=str(hrepo / "02_สตง/03_report_files/oag-2026-09.xlsx"), content="x") == 2
    assert f("Write", file_path=str(hrepo / "notes.md"), content="x") == 0
    assert f("Bash", command="rm 02_สตง/03_report_files/oag-2026-09.xlsx") == 2
    assert f("Bash", command="cp x.xlsx 01_ประปา/01_master/master_mwd.xlsx") == 2
    assert f("Bash", command="ls 01_ประปา/03_report_files") == 0
    assert f("Bash", command="python3 scripts/nnp_cli.py plan --org oag --month 2026-09") == 0
    assert f("Bash", command="python3 scripts/nnp_cli.py plan --org oag") == 2             # ไม่ระบุเดือน
    assert f("Bash", command="python3 scripts/nnp_cli.py begin --month 2026-09") == 2      # ไม่ระบุ org
    assert f("Bash", command="python3 scripts/nnp_cli.py check-env") == 0
    assert f("mcp__remote-devices__device_commit_files",
             files=[{"devicePath": "C:\\x\\02_สตง\\03_report_files\\a.xlsx"}]) == 2


def test_stop_guard_and_session_start(hrepo):
    assert hook(hrepo, "stop_guard.py", {})[1] == ""                                         # ไม่มีงานค้าง
    begin(hrepo)
    code, out, _ = hook(hrepo, "stop_guard.py", {})
    assert code == 0 and json.loads(out)["decision"] == "block" and "oag 2026-09" in out
    assert hook(hrepo, "stop_guard.py", {"stop_hook_active": True})[1] == ""                 # ไม่วนซ้ำ
    run_cli(hrepo, "abort", "--org", "oag", "--month", "2026-09")
    assert hook(hrepo, "stop_guard.py", {})[1] == ""
    code, out, _ = hook(hrepo, "session_start.py", {})
    assert code == 0 and "CLAUDE.md" in json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert (hrepo / ".run" / "hook-heartbeat").exists()
