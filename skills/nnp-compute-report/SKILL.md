---
name: nnp-compute-report
description: กฎการคำนวณแถวรายงาน (previousMonth, diff, remaining, สถานะ) และวิธีใช้ plan/apply ใช้เมื่อต้องอธิบายหรือตรวจตัวเลข
---

# คำนวณรายงาน

คำสั่ง: `plan` (ดูสถานะ+ผู้ชนะ+need_body) → `add-body` → `apply` (เขียน xlsx) · เรียกซ้ำได้ ผลเท่าเดิม (idempotent)

| ช่อง | กฎ |
|------|-----|
| unit, building | จาก master ตาม serial |
| previousMonth | totalCounter ของ serial เดียวกันในรายงานเดือนก่อน |
| diff | totalCounter − previousMonth |
| remaining | toner Black % เป็นเศษส่วน (100% = 1) |
| ไม่มีไฟล์เดือนก่อน | oag: previousMonth 0, diff = total · mwd: เว้นว่าง |
| เครื่องไม่อยู่ในไฟล์เดือนก่อน | previousMonth 0 · oag ระบายแดงทั้งแถว (FF6666), mwd ไม่ระบาย |
| serial ไม่อยู่ใน master | `ERROR_NO_MASTER` (ไม่เขียนแถว, รายงานในผลลัพธ์) |
| ข้อความที่ done แล้ว (COMPLETE/SKIPPED/SUPERSEDED) | ข้ามเมื่อรันซ้ำ; ERROR_* ถูกลองใหม่ · `--reprocess` ประมวลซ้ำทั้งหมด |
| แถวเดิมในรายงานใหม่กว่า | ข้อความที่เก่ากว่า = SUPERSEDED |

ถ้า `diff` ติดลบ → CLI ใส่ `notes` — ไม่แก้เอง รายงานให้คนตรวจ (มิเตอร์รีเซ็ต/เครื่องเปลี่ยน)
