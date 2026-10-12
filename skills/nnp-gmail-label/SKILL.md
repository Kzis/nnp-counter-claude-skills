---
name: nnp-gmail-label
description: สร้าง/หา label รายเดือนและติด label ให้ข้อความที่ประมวลแล้ว (ต้องใช้ label ID) ใช้หลัง apply
---

# Label

1. `python3 scripts/nnp_cli.py labels --org <org> --month <M>` → ได้ `label_name`, `message_ids` (ข้อความที่ต้องติด: COMPLETE + SUPERSEDED), `count`
   - dry-run: คืน `skip: true` (และ `label`, `would_label`) → **ไม่ติด label** ข้ามขั้นนี้และไปที่ audit/verify
2. `list_labels` → หา label ที่ชื่อตรงกับ `label_name` ทุกตัวอักษร
   - ไม่มี → `create_label(name=<label_name>)` (ครั้งเดียว) แล้วใช้ id ที่ได้
   - ชื่อ `zz-test-…` ใช้ได้เฉพาะรอบ `--env test`; ห้ามสร้าง label ชื่ออื่น
3. ติดทีละข้อความ: `label_message(messageId, labelIds=[<id>])` (หนึ่งข้อความต่อหนึ่งครั้ง) — ข้ามข้อความที่ติดอยู่แล้ว (`labelIds` ใน search มีอยู่แล้ว)
4. `python3 scripts/nnp_cli.py labeled --org <org> --month <M> --count <จำนวนที่ติดสำเร็จ> --label-id <id>`
   - จำนวนต้องเท่ากับ `count` — ไม่เท่า CLI ปฏิเสธ (ยังไม่นับว่าเสร็จ)

ข้อห้าม: ห้าม unlabel/ลบ label · ห้ามติด label องค์กรหรือเดือนอื่น
