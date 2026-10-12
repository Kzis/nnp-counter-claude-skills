---
name: nnp-counter-all
description: ประมวลผลอีเมลตัวนับของทั้ง สตง. (oag) และ ประปา (mwd) พร้อมกันสำหรับเดือนเดียวกัน ใช้เมื่อผู้ใช้พิมพ์ /nnp-counter-all {YYYY-MM}
---

# /nnp-counter-all {year-month}

สั่ง agent **oag** และ **mwd** ทำงาน **พร้อมกัน (parallel)** สำหรับเดือนเดียวกัน

## ขั้นตอน

1. อ่านเดือนจากอาร์กิวเมนต์ — กฎเดียวกับ `/nnp-counter-oag` (normalize เป็น `YYYY-MM`; **ไม่มีเดือน/อ่านไม่ออก = ถามกลับเสมอ** ด้วย AskUserQuestion; เดือนอนาคต = ถามยืนยัน)
2. อ่านตัวเลือก `--dry-run` / `--env test` / `--reprocess` / `--ignore-existing` (ส่งให้ทั้งสอง agent เหมือนกัน)
3. ประกาศ: `MONTH=YYYY-MM  ORGS=oag+mwd  MODE=...`
4. เรียก Agent tool **2 ครั้งใน message เดียวกัน** (เพื่อให้รันขนาน) ด้วย prompt ตามแม่แบบใน `skills/nnp-counter-oag/SKILL.md` และ `skills/nnp-counter-mwd/SKILL.md` — org ต่างกัน เดือนเดียวกัน
5. รอทั้งสองจบ แล้วรายงานรวมเป็นตาราง 2 แถว (oag / mwd): แถวที่ได้, สถานะ, ยังไม่ส่ง, verify, ปัญหา
   - ถ้าฝั่งใดล้มเหลว ฝั่งอื่นยังนับว่าสำเร็จ — รายงานแยก และบอกวิธีสั่งซ้ำเฉพาะฝั่งที่ล้ม (`/nnp-counter-<org> YYYY-MM`)

## ความปลอดภัยของการรันขนาน
- แต่ละ org มี config, โฟลเดอร์ข้อมูล, ticket (`.run/<org>-<ym>.json`) และ `_work/<org>/` แยกกัน → ไม่ชนกัน
- ห้ามให้ agent ตัวหนึ่งแตะข้อมูลของอีกองค์กร (hook ตรวจให้)
