"""Ctx = org + เดือน + โหมด (จริง/dry-run) + path ทั้งหมดที่เกี่ยวข้อง"""
from __future__ import annotations

from pathlib import Path

from . import naming
from .config import REPO_ROOT, OrgConfig, load_org


class Ctx:
    def __init__(self, org: str, ym: str, root: Path | str = REPO_ROOT, dry_run: bool = False,
                 env: str = "prod", reprocess: bool = False, sandbox: Path | str | None = None):
        self.root = Path(root)
        self.org = org
        self.ym = naming.validate_ym(ym)
        self.prev_ym = naming.shift_ym(self.ym, -1)
        self.cfg: OrgConfig = load_org(org, self.root)
        self.dry_run = dry_run
        self.env = env
        self.reprocess = reprocess
        self.sandbox = Path(sandbox) if sandbox else None
        if dry_run:
            if not self.sandbox:
                raise ValueError("dry-run ต้องมี sandbox")
            self.data_root = self.sandbox / self.cfg.data_dir
        else:
            self.data_root = self.root / self.cfg.data_dir
        self.work_dir = self.root / "_work" / org / self.ym
        self.run_dir = self.root / ".run"

    # ---- paths ----
    def dir(self, kind: str) -> Path:
        return self.data_root / self.cfg.dirs[kind]

    @property
    def master_path(self) -> Path:
        return self.dir("master") / self.cfg.master_file

    @property
    def report_path(self) -> Path:
        return self.dir("report") / naming.report_name(self.cfg, self.ym)

    @property
    def prev_report_path(self) -> Path:
        return self.dir("report") / naming.report_name(self.cfg, self.prev_ym)

    @property
    def history_path(self) -> Path:
        return self.dir("history") / naming.history_name(self.cfg, self.ym)

    @property
    def ticket_path(self) -> Path:
        return self.run_dir / f"{self.org}-{self.ym}.json"

    @property
    def label(self) -> str:
        return naming.label_name(self.cfg, self.ym, self.env)

    @property
    def query(self) -> str:
        return naming.gmail_query(self.cfg, self.ym)
