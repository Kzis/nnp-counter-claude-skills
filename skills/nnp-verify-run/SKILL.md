---
name: nnp-verify-run
description: ตรวจผลหลัง apply: audit สุ่มเทียบ Gmail แล้ว verify ปิด ticket ใช้ทุกครั้งก่อนจบงาน
---

# ตรวจและปิดงาน

1. `python3 scripts/nnp_cli.py audit --org <org> --month <M> --n 5` → ได้ตัวอย่าง `{id, serial, date, total}`
2. สำหรับแต่ละตัวอย่าง **เรียก `get_message(id, MINIMAL)` ใหม่จาก Gmail** (ห้ามใช้ค่าที่ตัวเองถอดไว้เทียบกับตัวเอง) เทียบ snippet: Date / Serial Number / Total Counter ต้องตรงกับค่าในตัวอย่าง → นับ `audited` และ `mismatch`
3. `python3 scripts/nnp_cli.py verify --org <org> --month <M> --audited <n> --audit-mismatch <m>`
   - รอบจริงต้องส่ง `--audited` เสมอ (ไม่ส่ง = ปฏิเสธ)
   - ทุก check ต้อง ok และ state = `verified` (dry-run ตรวจจากสถานะ applied)
   - mismatch > 0 → หยุด รายงานว่ามีการถอดค่าผิด ให้รัน `begin --fresh` แล้วทำใหม่
4. อ่าน `warnings` (diff ติดลบ, ERROR_*) ใส่ในรายงานสรุปเสมอ
Stop hook จะไม่ให้จบงานถ้า ticket ยังไม่ `verified`
