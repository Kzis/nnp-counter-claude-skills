---
name: nnp-file-create
description: สร้างไฟล์รายงาน/history/โฟลเดอร์ของเดือนที่ยังไม่มี ให้ถูกรูปแบบ ใช้เมื่อเริ่มเดือนใหม่
---

# สร้างไฟล์

ไม่ต้องสร้างเอง — `python3 scripts/nnp_cli.py begin --org <org> --month <YYYY-MM>` สร้างให้:
- โฟลเดอร์ `01_master / 02_historys / 03_report_files` ถ้าขาด
- `<prefix>-YYYY-MM.xlsx` (Sheet1 หัวคอลัมน์: machineDate, serialNumber, machineModel, unit, building, previousMonth, totalCounter, diff, remaining)
- `<prefix>-flow-history-YYYY-MM.xlsx` (Id, ThreadId, SerialNumber, Status, Timestamp)
- ผลอยู่ใน `created_files` ของผลลัพธ์ `begin`

กติกา: ไม่ทับไฟล์ที่มีอยู่ · ไม่สร้างถ้าไม่มี master (จะ error `ERROR_NO_MASTER` — ให้ผู้ใช้วาง master ก่อน) · แท็บ `missing` ถูกสร้าง/เขียนใหม่ตอน `apply` (ดู nnp-missing-sheet)
