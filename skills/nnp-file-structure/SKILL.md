---
name: nnp-file-structure
description: โครงสร้างโฟลเดอร์/ไฟล์มาตรฐานของ nnp-counter และวิธีให้ระบบจัด/ตรวจให้ถูก ใช้เมื่อต้องรู้ว่าไฟล์อะไรอยู่ที่ไหน
---

# โครงสร้างไฟล์มาตรฐาน

```
<โฟลเดอร์งาน>/
├─ CLAUDE.md                  กติกาและ flow หลัก
├─ agents/{oag,mwd}/          AGENT.md + config.yaml ของแต่ละองค์กร
├─ skills/                    ตัวช่วยย่อย + คำสั่ง /nnp-counter-*
├─ scripts/nnp_cli.py         ตัวคำนวณ/เขียน xlsx (ห้ามเขียนไฟล์ข้อมูลด้วยมือ)
├─ hooks/                     ตัวป้องกัน
├─ 01_ประปา/  (mwd)           01_master/master_mwd.xlsx · 02_historys/ · 03_report_files/
├─ 02_สตง/    (oag)           01_master/master_oag.xlsx · 02_historys/ · 03_report_files/
├─ .run/                      ticket ของแต่ละรอบ (<org>-<YYYY-MM>.json)
└─ _work/                     ไฟล์ชั่วคราว: <org>/<ym>/, dryrun/, backup/, inbox/
```

- **01_master** = รายชื่อเครื่อง (อ่านอย่างเดียว) · **02_historys** = ประวัติอีเมลที่ประมวลแล้ว · **03_report_files** = รายงานรายเดือน
- ทุกอย่างของแต่ละองค์กรเก็บใต้ `data_dir` ใน `agents/<org>/config.yaml`
- `begin` จัดโครงสร้างให้เองทุกครั้ง: สร้างโฟลเดอร์ที่ขาด, ย้ายไฟล์ที่วางผิดที่ (ไม่ทับ/ไม่ลบ), สร้างไฟล์ของเดือนนั้นถ้ายังไม่มี → ดู nnp-file-move, nnp-file-create
