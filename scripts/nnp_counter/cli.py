"""CLI: begin → add-meta → plan → add-body → apply → labels → labeled → verify (บังคับลำดับด้วย ticket)"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import emailparse as ep
from . import naming, structure, ticket, xlsxio
from .compute import DONE_RE, compute
from .config import ORGS, REPO_ROOT, TZ, NnpError
from .context import Ctx
from .missing import compute_missing
from .verify import verify as run_verify


def out(obj: dict, code: int = 0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def stamp_now() -> str:
    return dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def read_jsonl_stdin() -> list[dict]:
    rows = []
    for ln, line in enumerate(sys.stdin.read().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise NnpError(f"บรรทัด {ln} ไม่ใช่ JSON: {e}")
    return rows


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_ctx(a) -> tuple[Ctx, dict]:
    ym = naming.validate_ym(a.month)
    root = Path(a.root)
    base = Ctx(a.org, ym, root)
    t = ticket.load(base.ticket_path)
    ctx = Ctx(a.org, ym, root, dry_run=t["dry_run"], env=t["env"], reprocess=t["reprocess"],
              sandbox=t.get("sandbox"))
    return ctx, t


def history_status(ctx: Ctx) -> dict:
    rows = xlsxio.read_rows(ctx.history_path, "Sheet1")
    return {str(r["Id"]).strip(): str(r.get("Status") or "").strip() for r in rows if r.get("Id")}


def load_bodies(ctx: Ctx) -> dict:
    out_ = {}
    for r in read_jsonl(ctx.work_dir / "bodies.jsonl"):
        t = ep.parse_toner(r.get("toner") or r.get("text"))
        out_[r["id"]] = t
    return out_


def do_compute(ctx: Ctx):
    metas = read_jsonl(ctx.work_dir / "meta.jsonl")
    master = xlsxio.read_master(ctx.master_path, ctx.cfg)
    prev_rows = xlsxio.read_rows(ctx.prev_report_path, "Sheet1") if ctx.prev_report_path.exists() else []
    main_rows = xlsxio.read_rows(ctx.report_path, "Sheet1")
    res = compute(ctx.cfg, ctx.ym, metas, load_bodies(ctx), master, prev_rows, ctx.prev_report_path.exists(),
                  main_rows, history_status(ctx), stamp_now(), ctx.reprocess)
    return res, master, prev_rows


# ------------------------------------------------------------------ commands
def cmd_begin(a):
    ym = naming.validate_ym(a.month)
    root = Path(a.root)
    real = Ctx(a.org, ym, root, env=a.env, reprocess=a.reprocess)
    ticket.check_can_begin(real.ticket_path, a.dry_run, a.force)
    sandbox = None
    if a.ignore_existing and not a.dry_run:
        raise NnpError("--ignore-existing ใช้ได้เฉพาะกับ --dry-run")
    if a.dry_run:
        sandbox = structure.make_sandbox(root, a.org, ym)
        ctx = Ctx(a.org, ym, root, dry_run=True, env=a.env, reprocess=a.reprocess, sandbox=sandbox)
        structure.ensure_dirs(ctx)
        structure.seed_sandbox(real, ctx, a.ignore_existing)
        moves = {"moved": [], "conflicts": []}
    else:
        ctx = real
        structure.ensure_dirs(ctx)
        moves = structure.move_misplaced(ctx)
    if not ctx.master_path.exists():
        raise NnpError(f"ไม่พบไฟล์ master: {ctx.master_path}")
    created = structure.ensure_month_files(ctx)
    # begin = เริ่มรอบใหม่เสมอ: เก็บไฟล์ทำงานของรอบก่อนไว้ใน _work/archive/ (ไม่ลบ) กันข้อมูลค้างปนกับรอบนี้
    archived = None
    leftovers = [f for f in ctx.work_dir.glob("*") if f.is_file()] if ctx.work_dir.exists() else []
    if leftovers:
        arc = root / "_work" / "archive" / f"{a.org}-{ym}-{dt.datetime.now(TZ).strftime('%Y%m%d-%H%M%S')}"
        arc.mkdir(parents=True, exist_ok=True)
        for f in leftovers:
            f.rename(arc / f.name)
        archived = str(arc)
    ctx.work_dir.mkdir(parents=True, exist_ok=True)
    hist = history_status(ctx)
    done = sorted(i for i, s in hist.items() if DONE_RE.match(s))
    (ctx.work_dir / "done_ids.txt").write_text("\n".join(done), encoding="utf-8")
    t = {"org": a.org, "ym": ym, "dry_run": a.dry_run, "env": a.env, "reprocess": a.reprocess,
         "sandbox": str(sandbox) if sandbox else None, "state": "begun", "created": ticket.now_iso(),
         "query": ctx.query, "sender": ctx.cfg.sender, "label": ctx.label}
    ticket.save(ctx.ticket_path, t)
    out({"ok": True, "banner": f"ORG={a.org} MONTH={ym} MODE={'DRY-RUN' if a.dry_run else 'REAL'} ENV={a.env}",
         "display_name": ctx.cfg.display_name, "gmail_query": ctx.query, "sender": ctx.cfg.sender,
         "label": ctx.label, "report_file": str(ctx.report_path), "history_file": str(ctx.history_path),
         "created_files": created, "moved_files": moves["moved"], "move_conflicts": moves["conflicts"],
         "already_done_ids": len(done), "done_ids_file": str(ctx.work_dir / "done_ids.txt"),
         "dry_run_sandbox": str(sandbox) if sandbox else None, "archived_previous_work": archived,
         "next": "ค้นอีเมลด้วย gmail_query แล้วส่งผลเข้า add-meta"})


def cmd_add_meta(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "begun", "add-meta")
    existing = {r["id"] for r in read_jsonl(ctx.work_dir / "meta.jsonl")}
    done = {i for i, s in history_status(ctx).items() if DONE_RE.match(s)}
    acc, dup, done_n, bad_sender, bad = [], 0, 0, 0, []
    for r in read_jsonl_stdin():
        mid, text = r.get("id"), (r.get("text") or r.get("snippet") or "")
        if not mid or not text.strip():
            bad.append(r.get("id") or "?")
            continue
        sender = (r.get("sender") or "").lower()
        if sender and ctx.cfg.sender.lower() not in sender:
            bad_sender += 1
            continue
        if mid in existing:
            dup += 1
            continue
        if mid in done and not ctx.reprocess:
            done_n += 1
            continue
        existing.add(mid)
        acc.append({"id": mid, "threadId": r.get("threadId") or "", "internalDate": r.get("internalDate"),
                    "sender": r.get("sender") or "", "text": text})
    append_jsonl(ctx.work_dir / "meta.jsonl", acc)
    ticket.advance(t, "collecting")
    ticket.save(ctx.ticket_path, t)
    out({"ok": True, "accepted": len(acc), "duplicates": dup, "already_done": done_n,
         "rejected_wrong_sender": bad_sender, "rejected_invalid": bad,
         "total_in_meta": len(existing - done) if not ctx.reprocess else len(existing)})


def cmd_plan(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "collecting", "plan")
    res, _, _ = do_compute(ctx)
    plan = {"counts": res["counts"], "need_body": res["need_body"], "issues": res["issues"],
            "notes": res["notes"], "infos": res["infos"], "candidates": res["candidates"]}
    (ctx.work_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    ticket.advance(t, "planned")
    ticket.save(ctx.ticket_path, t)
    out({"ok": True, **plan, "need_body_count": len(res["need_body"]),
         "next": "ดึงเนื้อเต็มของ need_body (get_message PLAIN_TEXT) แล้วส่ง {id,toner} เข้า add-body; ถ้า need_body ว่างไป apply ได้เลย"})


def cmd_add_body(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "planned", "add-body")
    metas = {r["id"] for r in read_jsonl(ctx.work_dir / "meta.jsonl")}
    have = {r["id"] for r in read_jsonl(ctx.work_dir / "bodies.jsonl")}
    acc, unknown, no_toner = [], [], []
    for r in read_jsonl_stdin():
        mid = r.get("id")
        if mid not in metas:
            unknown.append(mid)
            continue
        if mid in have:
            continue
        tn = ep.parse_toner(r.get("toner") or r.get("text"))
        if not tn:
            no_toner.append(mid)
        have.add(mid)
        acc.append({"id": mid, "toner": f"{tn[0]} {tn[1]}" if tn else ""})
    append_jsonl(ctx.work_dir / "bodies.jsonl", acc)
    res, _, _ = do_compute(ctx)
    out({"ok": True, "accepted": len(acc), "unknown_ids": unknown, "no_toner_found": no_toner,
         "still_need_body": len(res["need_body"]), "need_body": res["need_body"][:50]})


def cmd_apply(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "planned", "apply")
    res, master, prev_rows = do_compute(ctx)
    if res["need_body"] and not a.allow_missing_body:
        raise NnpError(f"ยังขาดเนื้ออีเมล (ค่า toner) {len(res['need_body'])} ฉบับ เช่น {res['need_body'][:5]} "
                       f"— ส่งเข้า add-body ก่อน หรือใช้ --allow-missing-body")
    bk = structure.backup(ctx)
    rep = xlsxio.upsert_report(ctx.report_path, res["main_rows"], {s.upper() for s in res["flagged"]},
                               ctx.cfg.flag_color) if res["main_rows"] else {"added": 0, "updated": 0}
    his = xlsxio.upsert_history(ctx.history_path, res["history_rows"]) if res["history_rows"] else {"added": 0, "updated": 0}
    fresh_main = xlsxio.read_rows(ctx.report_path, "Sheet1")
    miss = compute_missing(master, fresh_main, prev_rows, ctx.prev_report_path.exists(), stamp_now())
    xlsxio.write_missing(ctx.report_path, miss["table"], miss["summary"])
    summary = {"counts": res["counts"], "report": rep, "history": his, "flagged": res["flagged"],
               "issues": res["issues"], "notes": res["notes"], "infos": res["infos"],
               "missing": {k: miss[k] for k in ("total", "sent", "missing", "dup_serials")},
               "label_message_ids": res["label_ids"],
               "rows": [{"id": r["id"], "serial": r["serial"], "date": r["emailDate"],
                         "total": r["row"]["totalCounter"]} for r in res["results"] if r["status"] == "COMPLETE"],
               "backup": bk}
    (ctx.work_dir / "apply.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    ticket.advance(t, "applied")
    ticket.save(ctx.ticket_path, t)
    brief = {k: v for k, v in summary.items() if k not in ("rows", "label_message_ids")}
    out({"ok": True, **brief, "label_count": len(res["label_ids"]), "dry_run": ctx.dry_run,
         "next": "dry-run: ไป verify" if ctx.dry_run else "ติด label (คำสั่ง labels) แล้วรายงานด้วย labeled"})


def cmd_labels(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "applied", "labels")
    s = json.loads((ctx.work_dir / "apply.json").read_text(encoding="utf-8"))
    if ctx.dry_run:
        out({"ok": True, "skip": True, "reason": "dry-run ไม่ติด label", "label": ctx.label,
             "would_label": len(s["label_message_ids"])})
    out({"ok": True, "label_name": ctx.label, "env": ctx.env, "message_ids": s["label_message_ids"],
         "count": len(s["label_message_ids"])})


def cmd_labeled(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "applied", "labeled")
    if ctx.dry_run:
        raise NnpError("dry-run ไม่ติด label — ข้ามขั้นนี้แล้วไป verify")
    exp = len(json.loads((ctx.work_dir / "apply.json").read_text(encoding="utf-8"))["label_message_ids"])
    if a.count != exp:
        raise NnpError(f"ติด label ได้ {a.count} แต่ต้องติด {exp} ข้อความ — ติดให้ครบก่อน (ข้ามที่ติดอยู่แล้วให้นับรวม)")
    t["labeled"] = {"count": a.count, "label_id": a.label_id, "at": ticket.now_iso()}
    ticket.advance(t, "labeled")
    ticket.save(ctx.ticket_path, t)
    out({"ok": True, "labeled": a.count, "next": "audit แล้ว verify"})


def cmd_audit(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "applied", "audit")
    rows = json.loads((ctx.work_dir / "apply.json").read_text(encoding="utf-8"))["rows"]
    if not rows:
        out({"ok": True, "sample": [], "note": "ไม่มีแถวให้ตรวจ"})
    n = min(a.n, len(rows))
    idx = sorted({round(i * (len(rows) - 1) / max(n - 1, 1)) for i in range(n)})
    out({"ok": True, "sample": [rows[i] for i in idx],
         "how": "get_message (MINIMAL) ของแต่ละ id แล้วเทียบ snippet: Date / Serial Number / Total Counter ต้องตรงกับ date/serial/total; "
                "นับจำนวนที่ตรวจและจำนวนที่ไม่ตรงส่งให้ verify (--audited / --audit-mismatch)"})


def cmd_verify(a):
    ctx, t = load_ctx(a)
    ticket.require(t, "applied" if ctx.dry_run else "labeled", "verify")
    r = run_verify(ctx)
    if a.audited is not None:
        r["checks"].append({"check": "audit ตัวอย่างกับ Gmail", "ok": (a.audit_mismatch or 0) == 0,
                            "detail": f"ตรวจ {a.audited} รายการ ไม่ตรง {a.audit_mismatch or 0}"})
        r["ok"] = all(c["ok"] for c in r["checks"])
    elif not ctx.dry_run:
        raise NnpError("รอบจริงต้อง audit ตัวอย่างกับ Gmail ก่อน: ส่ง --audited N --audit-mismatch M")
    if r["ok"]:
        ticket.advance(t, "verified")
        ticket.save(ctx.ticket_path, t)
    out({"ok": r["ok"], "state": t["state"], **r}, 0 if r["ok"] else 1)


def cmd_abort(a):
    ym = naming.validate_ym(a.month)
    t = ticket.abort(Ctx(a.org, ym, Path(a.root)).ticket_path)
    out({"ok": True, "state": t["state"], "was": t["state_before_abort"]})


def cmd_status(a):
    run_dir = Path(a.root) / ".run"
    items = []
    for p in sorted(run_dir.glob("*.json")) if run_dir.exists() else []:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if "org" in d and (not a.org or d["org"] == a.org) and (not a.month or d["ym"] == a.month):
                items.append({k: d.get(k) for k in ("org", "ym", "state", "dry_run", "env", "updated")})
        except Exception:
            pass
    out({"ok": True, "tickets": items})


def cmd_check_env(a):
    import importlib
    root = Path(a.root)
    res = {"python": sys.version.split()[0], "python_ok": sys.version_info >= (3, 10), "modules": {}, "folders": {}}
    for mod in ("openpyxl", "yaml"):
        try:
            m = importlib.import_module(mod)
            res["modules"][mod] = getattr(m, "__version__", "ok")
        except ImportError:
            res["modules"][mod] = None
    try:
        import pytest  # noqa
        res["modules"]["pytest(dev)"] = pytest.__version__
    except ImportError:
        res["modules"]["pytest(dev)"] = None
    for org in ORGS:
        try:
            ctx = Ctx(org, naming.current_ym(), root)
            res["folders"][org] = {"config": True, "master": ctx.master_path.exists(),
                                   "dirs": all(ctx.dir(k).exists() for k in ("master", "history", "report"))}
        except Exception as e:
            res["folders"][org] = {"config": False, "error": str(e)}
    hb = root / ".run" / "hook-heartbeat"
    res["hook_heartbeat"] = hb.read_text().strip() if hb.exists() else None
    res["ok"] = (res["python_ok"] and all(v for k, v in res["modules"].items() if not k.endswith("(dev)"))
                 and all(f.get("master") for f in res["folders"].values()))
    out(res, 0 if res["ok"] else 1)


def build_parser():
    p = argparse.ArgumentParser(prog="nnp_cli", description="nnp counter — ประมวลผลอีเมลรายงาน counter")
    p.add_argument("--root", default=str(REPO_ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, month=True):
        sp.add_argument("--org", required=True, choices=ORGS)
        if month:
            sp.add_argument("--month", required=True, help="YYYY-MM (บังคับ ไม่มีค่าเริ่มต้น)")

    sp = sub.add_parser("begin"); common(sp)
    sp.add_argument("--dry-run", action="store_true"); sp.add_argument("--env", default="prod", choices=["prod", "test"])
    sp.add_argument("--reprocess", action="store_true"); sp.add_argument("--force", action="store_true")
    sp.add_argument("--fresh", action="store_true", help="(คงไว้เพื่อความเข้ากันได้: begin เริ่มรอบใหม่เสมออยู่แล้ว)")
    sp.add_argument("--ignore-existing", action="store_true",
                    help="(เฉพาะ --dry-run) เริ่มจากไฟล์เดือนนี้ว่าง ไม่คัดลอกของเดิมมา ใช้เทียบผลกับของเดิม")
    sp.set_defaults(fn=cmd_begin)
    for name, fn in (("add-meta", cmd_add_meta), ("plan", cmd_plan), ("add-body", cmd_add_body), ("labels", cmd_labels)):
        sp = sub.add_parser(name); common(sp); sp.set_defaults(fn=fn)
    sp = sub.add_parser("apply"); common(sp); sp.add_argument("--allow-missing-body", action="store_true"); sp.set_defaults(fn=cmd_apply)
    sp = sub.add_parser("labeled"); common(sp); sp.add_argument("--count", type=int, required=True)
    sp.add_argument("--label-id"); sp.set_defaults(fn=cmd_labeled)
    sp = sub.add_parser("audit"); common(sp); sp.add_argument("--n", type=int, default=5); sp.set_defaults(fn=cmd_audit)
    sp = sub.add_parser("abort"); common(sp); sp.set_defaults(fn=cmd_abort)
    sp = sub.add_parser("verify"); common(sp); sp.add_argument("--audited", type=int)
    sp.add_argument("--audit-mismatch", type=int); sp.set_defaults(fn=cmd_verify)
    sp = sub.add_parser("status"); sp.add_argument("--org"); sp.add_argument("--month"); sp.set_defaults(fn=cmd_status)
    sp = sub.add_parser("check-env"); sp.set_defaults(fn=cmd_check_env)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except NnpError as e:
        out({"ok": False, "error": str(e)}, 2)
