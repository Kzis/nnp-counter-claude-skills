# nnp-counter — อ่านอีเมลตัวนับเครื่องถ่ายเอกสาร → รายงาน .xlsx รายเดือน

ระบบนี้ทำงาน **ในเครื่อง ผ่าน Claude Cowork เท่านั้น** (ไม่มี n8n, ไม่มี schedule — สั่งเป็นครั้งๆ)
แหล่งข้อมูลเดียวคือ **Gmail** (อ่าน + ติด label) ผลลัพธ์คือไฟล์ `.xlsx` ในโฟลเดอร์นี้

## คำสั่งสำหรับผู้ใช้
| คำสั่ง | ทำอะไร |
|--------|--------|
| `/init-nnp-counter-skills` | ตรวจ/เตรียมเครื่องให้พร้อม (ผู้ใช้ใหม่พิมพ์ก่อนเลย) |
| `/nnp-counter-oag {YYYY-MM}` | agent **oag** (สตง.) ทำเดือนที่ระบุ |
| `/nnp-counter-mwd {YYYY-MM}` | agent **mwd** (ประปา) ทำเดือนที่ระบุ |
| `/nnp-counter-all {YYYY-MM}` | รัน oag + mwd **พร้อมกัน** เดือนเดียวกัน |

ตัวเลือก: `--dry-run` (ซ้อมบนสำเนา ไม่แตะไฟล์จริง ไม่ติด label) · `--env test` (label ทดสอบ `zz-test-…`) · `--reprocess` (ประมวลซ้ำ)

## กฎบังคับ 3 ข้อ (ห้ามละเว้น)
1. **ต้องรู้เสมอว่าองค์กรไหน + เดือนไหน** — ไม่มีเดือน/อ่านไม่ออก → **ถามกลับเสมอ** (AskUserQuestion: เดือนที่แล้ว / เดือนนี้ / ระบุเอง) ห้ามเดา; เดือนอนาคตต้องถามยืนยัน
2. **หนึ่ง agent = หนึ่งองค์กร + หนึ่งเดือน** — ทุกคำสั่ง CLI ต้องมี `--org` และ `--month`; ค้น Gmail ด้วย `gmail_query` ที่ `begin` คืนมาตามตัวอักษร (มีช่วงเวลา epoch ของเดือนล็อกไว้)
3. **ห้ามจบงานก่อน `verify` ผ่าน** (state = `verified`)

## โครงสร้าง (ดู skills/nnp-file-structure)
```
agents/{oag,mwd}/AGENT.md + config.yaml   ← คำสั่งทำงานและค่าตั้งของแต่ละองค์กร
skills/                                   ← คำสั่ง /nnp-counter-* และ skills ย่อย (nnp-*)
scripts/nnp_cli.py                        ← ตัวคำนวณ + เขียน xlsx เดียวของระบบ
hooks/                                    ← ตัวป้องกัน (registered ใน .claude/settings.json)
01_ประปา/ (mwd)  02_สตง/ (oag)            ← 01_master · 02_historys · 03_report_files
.run/  _work/                             ← ticket ของแต่ละรอบ / ไฟล์ชั่วคราว (ไม่ใช่ข้อมูลจริง)
```
`.claude/skills/` เป็นสำเนาของ 4 คำสั่งหลักใน `skills/` — **แก้ที่ `skills/` แล้วคัดลอกทับ**

## Flow (ทุกองค์กรเหมือนกัน)
```
ผู้ใช้สั่ง /nnp-counter-<org|all> YYYY-MM
 └ entry skill: normalize เดือน / ถามกลับถ้าขาด → เรียก sub agent (all = 2 ตัวขนานใน message เดียว)
    └ agents/<org>/AGENT.md:
      0 โหลด Gmail tools (nnp-gmail-connect)
      1 begin        → จัดโฟลเดอร์/สร้างไฟล์เดือน/เปิด ticket (nnp-file-*)   [state: begun]
      2 ค้น Gmail    → add-meta (snippet ทุกข้อความ, ระดับ message ไม่ใช่ thread)  [collecting]
      3 plan         → จัดสถานะ + เลือกผู้ชนะต่อ serial + รายชื่อ need_body        [planned]
      4 add-body     → toner % เฉพาะผู้ชนะ (get_message PLAIN_TEXT)
      5 apply        → เขียน Sheet1 + history + แท็บ missing (สำรองก่อน)          [applied]
      6 labels       → ติด label <prefix>-YYYY-MM ทีละข้อความ → labeled           [labeled]
      7 audit→verify → สุ่มเทียบ Gmail + ตรวจไฟล์                                  [verified]
      8 รายงานสรุป
```
รายละเอียดแต่ละขั้น: ดู `skills/nnp-*/SKILL.md` ตามชื่อขั้นในตาราง `agents/<org>/AGENT.md`

## กติกาธุรกิจโดยย่อ (รายละเอียด: skills/nnp-compute-report, nnp-email-parse)
- สถานะ: `COMPLETE` (ผู้ชนะ) · `SUPERSEDED` (มีฉบับใหม่กว่าของ serial เดียวกันในเดือน) · `SKIPPED_OTHER_MONTH` · `ERROR_NO_SERIAL` · `ERROR_PARSE_DATE` · `ERROR_NO_MASTER` · `ERROR_BAD_SENDER`
- ผู้ชนะ = ข้อความที่ **วันที่ของเครื่อง** ล่าสุดต่อ serial; ERROR_* จะถูกลองใหม่รอบถัดไป ส่วน COMPLETE/SKIPPED/SUPERSEDED ถือว่าเสร็จ (รันซ้ำได้ผลเดิม)
- oag: ไม่มีไฟล์เดือนก่อน → previousMonth 0; เครื่องใหม่ระบายแดง · mwd: ไม่มีไฟล์เดือนก่อน → เว้นว่าง ไม่ระบายสี
- ผู้ส่ง: oag = `networkservice@oag.go.th` · mwd = `pachara.l@mwa.co.th`
- label: `oag-YYYY-MM` / `mwd-YYYY-MM` (ทดสอบ: `zz-test-…`)

## ความปลอดภัย (hooks + CLI)
- hooks (`hooks/*.py`): Gmail ใช้ได้เฉพาะอ่าน + ติด label ภายใต้ ticket ที่เปิดอยู่ และ query ต้องตรง ticket · ห้ามเขียนไฟล์ 01_master/02_historys/03_report_files นอก CLI · Stop ถูกบล็อกถ้า ticket ยังไม่ verified (ยกเลิกด้วย `abort`)
- ถ้า hooks ไม่ถูกโหลดในสภาพแวดล้อมนี้ **CLI ยังบังคับกติกาหลักเอง** (ต้องมี org+month, ลำดับ state, ล็อกไม่ให้รันงานจริงซ้อน, label ต้องครบ, รอบจริงต้อง audit ก่อน verify)
- รอบจริงสำรองไฟล์ที่ `_work/backup/` ก่อนแก้ · ไม่มีการลบไฟล์ · ค่าจากอีเมลที่ agent ถอดต้องคัดลอกตรงตัว (audit จะสุ่มตรวจ)

## ทดสอบ / ซ้อม
- `python3 -m pytest -q tests` — unit tests (ต้องผ่านทั้งหมด)
- `/nnp-counter-<org> YYYY-MM --dry-run` — ซ้อมบนสำเนาใน `_work/dryrun/…` (ใช้ `--ignore-existing` ของ begin ถ้าต้องการเทียบกับรายงานเดิม)

## ตัวอย่างคำสั่ง CLI (agent เรียกเอง)
`python3 scripts/nnp_cli.py begin --org oag --month 2026-09` → `add-meta` → `plan` → `add-body` → `apply` → `labels` → `labeled --count N` → `audit` → `verify --audited N --audit-mismatch M` · ช่วยเหลือ: `status`, `check-env`, `abort`
