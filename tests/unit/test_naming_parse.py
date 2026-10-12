import pytest

from nnp_counter import emailparse as ep
from nnp_counter import naming
from nnp_counter.config import NnpError, load_org
from tests.conftest import REPO

OAG_SNIPPET = ("Date : 28-09-2026 10:36 Machine Model : TOSHIBA e-STUDIO4528A Serial Number : CTAR33988 "
               "Total Counter : 12 Supplier: Name : Tel Number : E-Mail : Address : Customer: Name : Tel Number : E-Mail :")
FULL_BODY = ("\t\t\t\t\nDate\t\t: 01-09-2026 13:49\t\t\t\t\t\t\nMachine Model\t: TOSHIBA e-STUDIO3028A\nSerial Number\t: CTHQ25384\n"
             "Total Counter\t: 32493\t\t\t\n\nSupplier:\n\tName\t\t:\nPrinter Error History\n\n\tDate\t\tTime\t\tErrorCode\t\tCounter\n"
             "\nToner Cartridge Information:\n\n\tColor Code\t\t\t\t\tBlack\n\nToner Information\n\n\tToner\t\t\t Remaining Quantity (%)\n"
             "\t------------\n\tBlack\t\t\t\t\t\t\t 4")


@pytest.mark.parametrize("v", ["2026-9", "26-09", "2026/09", "2026-13", "2026-00", "", "เดือนนี้", "2026-09-01"])
def test_validate_ym_rejects(v):
    with pytest.raises(NnpError):
        naming.validate_ym(v)


def test_validate_ym_ok():
    assert naming.validate_ym(" 2026-09 ") == "2026-09"


def test_shift_and_bounds():
    assert naming.shift_ym("2026-01", -1) == "2025-12"
    assert naming.shift_ym("2026-12", 1) == "2027-01"
    assert naming.month_bounds_epoch("2026-09") == (1788195600, 1790787600)  # เวลาไทย (UTC+7)


def test_names_and_classify():
    cfg = load_org("oag", REPO)
    assert naming.report_name(cfg, "2026-09") == "oag-2026-09.xlsx"
    assert naming.history_name(cfg, "2026-09") == "oag-flow-history-2026-09.xlsx"
    assert naming.label_name(cfg, "2026-09") == "oag-2026-09"
    assert naming.label_name(cfg, "2026-09", "test") == "zz-test-oag-2026-09"
    assert naming.classify(cfg, "oag-2026-09.xlsx") == ("report", "2026-09")
    assert naming.classify(cfg, "oag-flow-history-2026-09.xlsx") == ("history", "2026-09")
    assert naming.classify(cfg, "master_oag.xlsx") == ("master", None)
    assert naming.classify(cfg, "mwd-2026-09.xlsx") == (None, None)
    assert naming.classify(cfg, "oag-2026-13.xlsx") == (None, None)
    assert naming.gmail_query(cfg, "2026-09") == "from:networkservice@oag.go.th after:1788195600 before:1790787600"


def test_parse_snippet():
    f = ep.parse_fields(OAG_SNIPPET)
    assert f == {"machineDate": "28-09-2026 10:36", "machineModel": "TOSHIBA e-STUDIO4528A",
                 "serialNumber": "CTAR33988", "totalCounter": "12"}


def test_parse_full_body_and_toner():
    f = ep.parse_fields(FULL_BODY)
    assert (f["machineDate"], f["serialNumber"], f["totalCounter"]) == ("01-09-2026 13:49", "CTHQ25384", "32493")
    assert f["machineModel"] == "TOSHIBA e-STUDIO3028A"
    assert ep.parse_toner(FULL_BODY) == ("Black", "4")          # ไม่หลงไปจับ "Toner Cartridge Information"
    assert ep.parse_toner("Black 99") == ("Black", "99")
    assert ep.parse_toner("ไม่มีข้อมูล") is None


def test_parse_date_formats():
    ms = ep.parse_date("28-09-2026 10:36")
    assert ep.fmt_date(ms) == "28-09-2026 10:36" and ep.ym_of(ms) == "2026-09"
    assert ep.parse_date("2026-09-28 10:36") == ms
    assert ep.parse_date("'28-09-2026 10:36") == ms          # มี ' นำหน้าจาก Sheets
    assert ep.fmt_date(ep.parse_date("09-28-2026 10:36")) == "28-09-2026 10:36"  # สลับ เดือน/วัน
    assert ep.parse_date("ไม่ใช่วันที่") is None and ep.parse_date(None) is None
    assert ep.parse_date("31-02-2026 10:00") is None
