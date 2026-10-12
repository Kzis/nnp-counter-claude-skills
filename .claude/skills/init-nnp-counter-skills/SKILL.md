---
name: init-nnp-counter-skills
description: ตรวจและเตรียมเครื่องให้รันโปรเจกต์ nnp-counter ได้ใน Claude Cowork (Python, แพ็กเกจ, Gmail, โฟลเดอร์, master, hooks) ผู้ใช้ใหม่พิมพ์ /init-nnp-counter-skills เมื่อเข้าโฟลเดอร์งานครั้งแรก
---

# /init-nnp-counter-skills — เตรียมระบบให้พร้อมใช้งาน

ทำเป็นเช็คลิสต์ ทีละข้อ รายงานเป็นตาราง ✅/❌ พร้อมวิธีแก้ของข้อที่ไม่ผ่าน **ไม่แก้ข้อมูลธุรกิจ ไม่ติด label ไม่ส่งอีเมล**

## เช็คลิสต์
1. **Cowork เชื่อมโฟลเดอร์งาน** — `ls` ที่โฟลเดอร์ (ต้องเห็น CLAUDE.md, scripts/, agents/, 01_ประปา, 02_สตง). ไม่เห็น → ให้ผู้ใช้เลือก/เชื่อมโฟลเดอร์ nnp ในแอป Claude แล้วเปิดงานใหม่
2. **Python ≥ 3.10** — `python3 --version`. ไม่มี → ติดตั้งจาก python.org (Windows ติ๊ก "Add to PATH")
3. **แพ็กเกจ** — `pip install -r requirements.txt` (openpyxl, pyyaml). ถ้าต้องการรันเทสต์: `pip install -r requirements-dev.txt`
4. **ตรวจสภาพแวดล้อมรวม** — `python3 scripts/nnp_cli.py check-env` ต้องได้ `"ok": true` (config, master, โฟลเดอร์ของ oag และ mwd)
5. **ไฟล์ master** — `01_ประปา/01_master/master_mwd.xlsx` และ `02_สตง/01_master/master_oag.xlsx` ต้องมี; ไม่มี → ให้ผู้ใช้วางไฟล์ (ระบบสร้างให้ไม่ได้)
6. **Gmail connector** — ToolSearch โหลดเครื่องมือ Gmail แล้วเรียก `list_labels` (อ่านอย่างเดียว) ต้องได้รายการ. ไม่ได้ → ให้ผู้ใช้เชื่อม Gmail ใน Settings → Connectors → Gmail (บัญชีที่รับอีเมลตัวนับ)
7. **ทดสอบหน่วย (ไม่บังคับ)** — `python3 -m pytest -q tests` ต้องผ่านทั้งหมด
8. **Hooks ทำงานหรือไม่** — รัน `date +%s` ด้วย Bash แล้วดูไฟล์ `.run/hook-heartbeat`: ถ้าเวลาใหม่ (ภายใน ~1 นาที) = hooks ทำงาน; ถ้าไม่มี/เก่า = hooks ไม่ถูกโหลดในสภาพแวดล้อมนี้ → **ยังใช้งานได้** เพราะ CLI บังคับกติกาหลักเอง (ต้องมี --org/--month, ลำดับขั้น, ล็อก, verify) แต่แจ้งผู้ใช้ว่าตัวกันระดับ hook ไม่ทำงาน
9. **Skills พร้อมใช้** — ยืนยันว่าพิมพ์ `/nnp-counter-oag`, `/nnp-counter-mwd`, `/nnp-counter-all` ได้ (ปรากฏในรายการ skills). ไม่ปรากฏ → ดูหัวข้อ "ติดตั้ง skills" ด้านล่าง

## ติดตั้ง skills (ครั้งเดียว)
คำสั่งหลัก 4 ตัวอยู่ในโฟลเดอร์ `skills/` (และสำเนาใน `.claude/skills/`) ถ้า Cowork ไม่เห็นให้ propose_skills เป็นการ์ดให้ผู้ใช้กดบันทึก 4 ตัว: init-nnp-counter-skills, nnp-counter-oag, nnp-counter-mwd, nnp-counter-all (เนื้อหาจากไฟล์ SKILL.md ในโฟลเดอร์ตามตัวอักษร)

## ปิดท้าย
สรุป: พร้อม / ไม่พร้อม (ข้อไหน) และบอกวิธีเริ่ม: `/nnp-counter-all 2026-09` (ลองก่อนด้วย `--dry-run` ได้: ซ้อมบนสำเนา ไม่แตะไฟล์จริง ไม่ติด label)
