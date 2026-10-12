---
name: nnp-file-naming
description: กติกาตั้งชื่อไฟล์ ป้ายกำกับ (label) และ ticket ของ nnp-counter ใช้เมื่อต้องตั้ง/ตรวจชื่อ
---

# การตั้งชื่อ

`<prefix>` = `oag` หรือ `mwd` · `YYYY-MM` = เดือนค.ศ. 2 หลัก เช่น `2026-09`

| อะไร | ชื่อ | อยู่ที่ |
|------|------|--------|
| master | `master_<prefix>.xlsx` | `<data_dir>/01_master/` |
| history | `<prefix>-flow-history-YYYY-MM.xlsx` | `<data_dir>/02_historys/` |
| รายงาน | `<prefix>-YYYY-MM.xlsx` | `<data_dir>/03_report_files/` |
| Gmail label | `<prefix>-YYYY-MM` (โหมด `--env test`: `zz-test-<prefix>-YYYY-MM`) | Gmail |
| ticket | `<org>-YYYY-MM.json` | `.run/` |

- ชื่อทั้งหมดมาจาก `scripts/nnp_counter/naming.py` — **ห้ามสร้างชื่อเอง** ให้ใช้ค่าที่ `begin` คืนมา (`report_file`, `history_file`, `label`)
- เดือนต้องเป็น `YYYY-MM` (เดือน 01–12) ไม่เช่นนั้น CLI ปฏิเสธ
- Gmail query = `from:<sender> after:<epoch เริ่มเดือน UTC+7> before:<epoch เริ่มเดือนถัดไป>`
