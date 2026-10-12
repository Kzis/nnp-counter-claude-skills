# ผลทดสอบขั้น 0 (12 ต.ค. 2026)

| หัวข้อ | ผล | ผลต่อการออกแบบ |
|---|---|---|
| sub agent เรียก Gmail | ได้ (ต้อง ToolSearch โหลด tool ก่อน) | agent mwd/oag เรียก Gmail เองได้ |
| sub agent เรียก device_bash | ได้ | agent รัน Python ที่ local ได้ |
| ขอบเขตวันที่ใน query | `after:<epoch> before:<epoch>` ใช้ได้ ตรงขอบเดือน (เวลาไทย) | ใช้ epoch ตามเวลา Asia/Bangkok ไม่ต้องขยายช่วง |
| จำนวนอีเมลต่อ thread | มีได้ถึง 100 (mwd 2026-09: 26 threads, ~249 อีเมล) | ต้องทำงานระดับ message ไม่ใช่ thread; search แสดง preview แค่ 5 อีเมลแรก |
| ขนาดผลลัพธ์ | get_thread 14 อีเมล ≈ 65,000 ตัวอักษร (เกินลิมิต, ถูกบันทึกลงไฟล์ฝั่งคลาวด์) | ห้ามดึงเนื้อเต็มทุกอีเมล: ใช้ snippet (Date/Model/Serial/Total) ก่อน แล้วดึงเนื้อเต็มเฉพาะอีเมลที่ชนะ (ต้องใช้ % toner) |
| snippet | มี Date, Machine Model, Serial Number, Total Counter (ไม่มี toner) | ใช้ตัดสิน COMPLETE/SUPERSEDED ได้โดยไม่ต้องโหลดเนื้อ |
| label | ใช้ label ID; มี `mwd-2026-09` (Label_10, 249 อีเมล), `zz-test-oag-2026-09` (Label_15, 1 อีเมล) อยู่แล้ว | ทดสอบ label ใช้ prefix `zz-test-` เท่านั้น |
| Python บน VM | 3.10.12 + openpyxl 3.1.5 + pyyaml; pytest ติดตั้งผ่าน pip ได้ | init skill ตรวจ/ติดตั้งทุก session |
| ข้อมูลทดสอบเดือน 9 | mwd: มีผล n8n ครบ (golden); oag: มีอีเมลทดสอบ 1 ฉบับ (CTAR33988, 28-09-2026) | ใช้ทดสอบทั้งสองชุด |
