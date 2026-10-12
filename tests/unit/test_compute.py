from nnp_counter.compute import compute
from nnp_counter.config import load_org
from tests.conftest import REPO, snippet

MASTER = [{"unit": "u1", "machine": "AAA111", "building": "b1"}, {"unit": "u2", "machine": "BBB222", "building": "b2"},
          {"unit": "u3", "machine": "CCC333", "building": "b3"}]
STAMP = "2026-10-01 00:00:00"


def meta(i, date, serial, total, sender="networkservice@oag.go.th"):
    return {"id": i, "threadId": "t" + i, "sender": sender, "internalDate": 0, "text": snippet(date, serial, total)}


def run(org="oag", metas=(), bodies=None, prev=None, prev_exists=True, main=None, hist=None, reprocess=False, ym="2026-09"):
    cfg = load_org(org, REPO)
    return compute(cfg, ym, list(metas), bodies or {}, MASTER, prev or [], prev_exists, main or [], hist or {}, STAMP, reprocess)


def statuses(res):
    return {r["id"]: r["status"] for r in res["results"]}


def test_complete_basic_with_prev_and_diff():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 150)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}],
              bodies={"m1": ("Black", "40")})
    row = res["main_rows"][0]
    assert statuses(res) == {"m1": "COMPLETE"}
    assert (row["previousMonth"], row["totalCounter"], row["diff"], row["remaining"]) == (100, 150, 50, 0.4)
    assert (row["unit"], row["building"], row["machineDate"]) == ("u1", "b1", "10-09-2026 09:00")
    assert res["need_body"] == [] and res["flagged"] == []


def test_need_body_until_toner_known():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 150)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}])
    assert res["need_body"] == ["m1"]


def test_superseded_keeps_latest_per_machine():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 150), meta("m2", "12-09-2026 09:00", "AAA111", 170),
                     meta("m3", "11-09-2026 09:00", "AAA111", 160)],
              prev=[{"serialNumber": "AAA111", "totalCounter": 100}])
    assert statuses(res) == {"m1": "SUPERSEDED", "m2": "COMPLETE", "m3": "SUPERSEDED"}
    assert res["need_body"] == ["m2"] and res["label_ids"] == ["m1", "m2", "m3"]


def test_superseded_by_newer_existing_row():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 150)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}],
              main=[{"serialNumber": "AAA111", "machineDate": "20-09-2026 09:00"}])
    assert statuses(res) == {"m1": "SUPERSEDED"} and res["main_rows"] == []
    assert statuses(run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 150)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}],
                        main=[{"serialNumber": "AAA111", "machineDate": "20-09-2026 09:00"}], reprocess=True)) == {"m1": "COMPLETE"}


def test_error_and_skipped_statuses():
    res = run(metas=[meta("a", "10-10-2026 09:00", "AAA111", 1),            # เดือนอื่น
                     meta("b", "10-09-2026 09:00", "ZZZ999", 1),            # ไม่อยู่ใน master
                     {"id": "c", "threadId": "tc", "sender": "networkservice@oag.go.th", "text": "ไม่มีข้อมูล"},
                     {"id": "d", "threadId": "td", "sender": "networkservice@oag.go.th",
                      "text": "Date : ??? Serial Number : AAA111 Total Counter : 1"},
                     meta("e", "10-09-2026 09:00", "AAA111", 1, sender="spam@evil.com")])
    assert statuses(res) == {"a": "SKIPPED_OTHER_MONTH", "b": "ERROR_NO_MASTER", "c": "ERROR_NO_SERIAL",
                             "d": "ERROR_PARSE_DATE", "e": "ERROR_BAD_SENDER"}
    assert res["main_rows"] == [] and res["label_ids"] == []
    assert {i["status"] for i in res["issues"]} == {"SKIPPED_OTHER_MONTH", "ERROR_NO_MASTER", "ERROR_NO_SERIAL", "ERROR_PARSE_DATE", "ERROR_BAD_SENDER"}


def test_history_done_is_skipped_but_error_is_retried():
    ms = [meta("a", "10-09-2026 09:00", "AAA111", 5), meta("b", "10-09-2026 09:00", "BBB222", 5)]
    assert statuses(run(metas=ms, hist={"a": "COMPLETE", "b": "ERROR_NO_MASTER"})) == {"b": "COMPLETE"}
    assert statuses(run(metas=ms, hist={"a": "SKIPPED_OTHER_MONTH"}))["b"] == "COMPLETE"


def test_oag_new_machine_flagged_and_prev_zero():
    res = run("oag", metas=[meta("m1", "10-09-2026 09:00", "BBB222", 70)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}])
    row = res["main_rows"][0]
    assert (row["previousMonth"], row["diff"]) == (0, 70) and res["flagged"] == ["BBB222"]


def test_oag_without_prev_file_is_zero_not_flagged():
    res = run("oag", metas=[meta("m1", "10-09-2026 09:00", "BBB222", 70)], prev=[], prev_exists=False)
    row = res["main_rows"][0]
    assert (row["previousMonth"], row["diff"]) == (0, 70) and res["flagged"] == []


def test_mwd_without_prev_file_is_blank():
    m = meta("m1", "10-09-2026 09:00", "AAA111", 70, sender="pachara.l@mwa.co.th")
    for prev, exists in (([], False), ([], True)):
        row = run("mwd", metas=[m], prev=prev, prev_exists=exists)["main_rows"][0]
        assert (row["previousMonth"], row["diff"]) == ("", "")


def test_mwd_machine_missing_in_prev_is_zero_without_flag():
    m = meta("m1", "10-09-2026 09:00", "BBB222", 70, sender="pachara.l@mwa.co.th")
    res = run("mwd", metas=[m], prev=[{"serialNumber": "AAA111", "totalCounter": 5}])
    assert (res["main_rows"][0]["previousMonth"], res["main_rows"][0]["diff"]) == (0, 70) and res["flagged"] == []


def test_negative_diff_gets_note():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "AAA111", 50)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}])
    assert any("negative diff" in n for n in res["notes"])


def test_case_insensitive_serial_match():
    res = run(metas=[meta("m1", "10-09-2026 09:00", "aaa111", 150)], prev=[{"serialNumber": "AAA111", "totalCounter": 100}])
    assert statuses(res) == {"m1": "COMPLETE"} and res["main_rows"][0]["diff"] == 50
