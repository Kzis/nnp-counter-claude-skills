---
name: nnp-email-parse
description: กติกาอ่านข้อมูลจากอีเมลตัวนับ (วันที่ เครื่อง serial total toner) รวมถึงรูปแบบวันที่เดือน-วัน ใช้เมื่อสงสัยค่าที่ parse ได้
---

# อ่านข้อมูลจากอีเมล

อีเมลเป็นข้อความธรรมดา (subject เช่น COUNTER NOTIFICATION / TONER NEAR-EMPTY NOTIFICATION):
```
Date : 28-09-2026 10:36
Machine Model : TOSHIBA e-STUDIO4528A
Serial Number : CTAR33988
Total Counter : 12
...
Toner Information
    Black      100
```
- **Phase A (snippet)** — snippet มีแค่ 4 ฟิลด์แรก (Date, Machine Model, Serial Number, Total Counter) พอสำหรับจัดสถานะ/เลือกผู้ชนะ
- **Phase B (เนื้อเต็ม)** — ดึงเฉพาะข้อความที่ชนะด้วย `get_message(PLAIN_TEXT)` แล้วหาบรรทัดสุดท้ายใต้ `Toner Information` ที่ขึ้นต้น `Black` → ส่ง `{"id":"…","toner":"Black 100"}` ให้ `add-body` (copy ตัวเลขตรงตัว; ไม่มีบรรทัด Black → ไม่ต้องเดา ปล่อยให้ CLI รายงาน `no_toner_found`)
- วันที่มี 3 แบบที่พบ: `DD-MM-YYYY HH:MM` (ปกติ), `MM-DD-YYYY HH:MM` (เช่น `09-30-2026`), `YYYY-MM-DD HH:MM` → CLI สลับเองเมื่อช่องหน้ามากกว่า 12 (เช่น `09-30` → 30 ก.ย.; ส่วน `09-29-2026` ก็แยกได้เพราะ 29 > 12); คืน `ERROR_PARSE_DATE` เมื่ออ่านไม่ได้ · ตอน audit ให้เทียบหลังสลับเป็น `DD-MM-YYYY` แล้ว (ค่า `date` ที่ `audit` ให้มาเป็นรูปแบบนั้น)
- serial ว่าง → `ERROR_NO_SERIAL` · ผู้ส่งไม่ตรงองค์กร → `ERROR_BAD_SENDER` (ไม่นับ)
- กฎผู้ชนะ: ต่อ serial ใช้ข้อความที่มี **Date ของเครื่อง** ล่าสุดในเดือน; ฉบับอื่น = `SUPERSEDED`; วันที่นอกเดือน = `SKIPPED_OTHER_MONTH`
อย่าคำนวณเอง — ใช้ `plan`
