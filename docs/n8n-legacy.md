# n8n legacy spec (ข้อมูลอ้างอิงเท่านั้น — ระบบปัจจุบันไม่ใช้ n8n)

คัดลอกจาก README เดิมของแต่ละโฟลเดอร์ก่อนเปลี่ยนเป็นคู่มือการใช้งาน ใช้เทียบกติกาธุรกิจเมื่อสงสัยเท่านั้น

---

# ส่วนที่ 1: ประปา (mwd)

# 01_ประปา — ระบบเก็บ Counter เครื่องถ่ายเอกสาร (การประปานครหลวง / MWA)

เอกสารนี้อธิบายการทำงานของชุด workflow **mwd** ใน n8n (project `os9TBq7Y6zz7S0Iy`) ที่อ่านอีเมลรายงานเครื่องถ่ายเอกสาร → สกัดข้อมูล → คำนวณ → บันทึกลง Google Sheet รายเดือน
เขียนขึ้นเพื่อใช้เป็นต้นแบบในการถอด n8n ออกแล้วย้ายไปเป็น skills / scheduled task / hooks ของ Claude (ดูหัวข้อ 9)

> อ้างอิงจากการอ่าน workflow จริง ณ วันที่ 12 ต.ค. 2026 (workflow ถูกแก้ล่าสุด 10 ต.ค. 2026)
> ไฟล์ `.xlsx` ในโฟลเดอร์นี้เป็นสำเนาที่ export จาก Google Sheets — **แหล่งข้อมูลจริงของ flow อยู่ใน Google Drive** ไม่ใช่โฟลเดอร์นี้

---

## 1. ภาพรวม

- เครื่องถ่ายเอกสาร Toshiba ของการประปาส่งอีเมลรายงานอัตโนมัติ (1 อีเมล = 1 เครื่อง) มาจากผู้ส่ง **`pachara.l@mwa.co.th`**
- Flow อ่านอีเมลเหล่านั้น แกะค่า Date / Model / Serial / Total Counter / Toner% แล้วเทียบกับ master (เครื่อง → หน่วยงาน, อาคาร)
- คำนวณส่วนต่างจากเดือนก่อน (`diff = totalCounter − previousMonth`) แล้วเขียนลงไฟล์รายเดือน `mwd-YYYY-MM`
- ติด Gmail label `mwd-YYYY-MM` ให้อีเมลที่ประมวลผลแล้ว
- เขียน sheet `missing` ในไฟล์เดือนนั้นทุกรอบ เพื่อบอกว่าเครื่องไหนใน master **ยังไม่ส่งข้อมูล**
- มี 2 workflow ที่ทำงานคู่กัน:

| Workflow | ID | หน้าที่ |
|---|---|---|
| `02_create_files_mwd` | `vePZfHcMqNnjxn4g` | สร้างไฟล์ Google Sheet + Gmail label ของเดือนปัจจุบัน (รันซ้ำได้ปลอดภัย) |
| `01_counter_mwd` | `7bkIyMybfcHyyiC2` | อ่านอีเมล → คำนวณ → เขียนข้อมูล → ติด label → อัปเดต sheet `missing` |

`01_counter_mwd` เรียก `02_create_files_mwd` ก่อนทุกรอบ (รอจนเสร็จ) เพื่อให้ไฟล์เดือนใหม่ถูกสร้างตั้งแต่รอบแรกของเดือน
Flow รุ่นเก่า (`03_mwd_counter_m`, `01_create_files_main_m`, `02_create_files_history_m`) ถูกปิดใช้งานแล้ว และถูกแทนที่ด้วย 2 flow ข้างต้น

---

## 2. โครงสร้างโฟลเดอร์ (เหมือน `02_สตง`)

```
01_ประปา/
├── README.md
├── 01_master/
│   └── master_mwd.xlsx              # ข้อมูลเครื่อง: machine(serial) → unit, building
├── 02_historys/
│   └── mwd-flow-history-YYYY-MM.xlsx   # log การประมวลผลอีเมลรายเดือน (กันทำซ้ำ)
└── 03_report_files/
    └── mwd-YYYY-MM.xlsx             # รายงานรายเดือน (Sheet1 = ข้อมูล, missing = เครื่องที่ยังไม่ส่ง)
```

ณ ปัจจุบัน: report `2025-11` ถึง `2026-10` (12 ไฟล์), history `2025-12` ถึง `2026-10` (11 ไฟล์), master 1 ไฟล์

> หมายเหตุ: workflow `02_create_files_mwd` สร้างไฟล์ที่ root ของ My Drive และ **ไม่ได้ย้ายเข้า folder** (ต่างจาก oag ที่ย้ายเข้า `03_report_files` / `02_historys` อัตโนมัติ) การจัดโฟลเดอร์ 01/02/03 ของชุดนี้จึงทำด้วยมือ/ในเครื่อง ถ้าต้องการให้ Drive ตรงกันต้องเพิ่มขั้นตอน move แบบเดียวกับ oag

---

## 3. ข้อมูลต้นทาง: อีเมลรายงานเครื่อง

- ผู้ส่ง: `pachara.l@mwa.co.th` (ตั้งไว้ 2 จุด: node `Gmail Trigger` > Filters > Sender และ query ใน node `List Month Emails`)
- เนื้อหาเป็นข้อความ plain text ที่มีบรรทัดรูปแบบ:

```
Date : 01-10-2026 10:39
Machine Model : TOSHIBA e-STUDIO4528A
Serial Number : CTHN52964
Total Counter : 140978
Toner Information
Black   4
Cyan    ...
```

Regex ที่ใช้แกะ (node `Parse + Compute`):

| ฟิลด์ | Pattern |
|---|---|
| `machineDate` | `/Date\s*:\s*(.*)/` |
| `machineModel` | `/Machine Model\s*:\s*(.*)/` |
| `serialNumber` | `/Serial Number\s*:\s*(\S+)/` (ใช้ token แรกก่อนช่องว่าง) |
| `totalCounter` | `/Total Counter\s*:\s*(\d+)/` |
| toner | อ่านส่วนหลังคำว่า `Toner Information` ด้วย `/(Black\|Cyan\|Magenta\|Yellow)\s+(\d+)/g` — **ใช้เฉพาะสีแรก (`toner[0]`)** มาเป็น `remaining` เช่น `4%` |

การอ่านวันที่ (`parseDate`) รองรับ: `yyyy-MM-dd[ HH:mm]`, `dd-MM-yyyy[ HH:mm]` (ถ้าเดือน > 12 และวัน ≤ 12 จะสลับให้), ตัวเลข serial ของ Excel — ตีความเป็น UTC ตามที่เขียนในอีเมล (ไม่แปลง timezone) แล้วเก็บเป็นข้อความรูป `dd-MM-yyyy HH:mm`

---

## 4. โครงสร้างข้อมูล (Schema)

### 4.1 master — `master_mwd` (Google Sheet ID `1GreO344YHG2ztriQTMtp2giJVizu6lGqNOJLtnll60U`)

| คอลัมน์ | ความหมาย | flow ใช้? |
|---|---|---|
| `unit` | ชื่อหน่วยงาน | ใช่ |
| `building` | อาคาร/ชั้น/ที่ตั้ง | ใช่ |
| `machine` | Serial Number ของเครื่อง (คีย์ที่ใช้จับคู่กับอีเมล) | ใช่ |
| `start`, `current`, `count` | ข้อมูลเสริมในชีตเดิม | ไม่ใช้ |

- อ่านจากแท็บแรกของไฟล์ (ไม่ได้ระบุชื่อแท็บ) ปัจจุบันมีเครื่อง **119 เครื่อง**
- serial ซ้ำใน master นับครั้งเดียว · ค่าในช่อง `machine` ที่ไม่ใช่ serial จะค้างในรายการ "ยังไม่ส่ง" จนกว่าจะแก้ master

### 4.2 report รายเดือน — `mwd-YYYY-MM`

**แท็บ `Sheet1`** (ห้ามเปลี่ยนชื่อแท็บ/ชื่อหัวคอลัมน์ เพราะ flow อ้างอิงด้วยชื่อ) — คีย์ของแถวคือ `serialNumber`

| คอลัมน์ | ที่มา |
|---|---|
| `machineDate` | วันที่ในอีเมล รูป `dd-MM-yyyy HH:mm` (เขียนนำหน้าด้วย `'` ให้ Sheets เก็บเป็นข้อความ) |
| `serialNumber` | จากอีเมล |
| `machineModel` | จากอีเมล |
| `unit` / `building` | จาก master |
| `previousMonth` | `totalCounter` ของเครื่องเดียวกันในไฟล์เดือนก่อน (ว่างถ้าไม่มีไฟล์เดือนก่อน) |
| `totalCounter` | จากอีเมล |
| `diff` | `totalCounter − previousMonth` (ว่างถ้าไม่มีไฟล์เดือนก่อน) |
| `remaining` | % toner (สีแรก) |

**แท็บ `missing`** — สร้างและเขียนทับโดย flow (อ่านอย่างเดียว อย่าแก้ด้วยมือ)

- ตาราง A:D → `unit`, `machine`, `building`, `reportedLastMonth` (`ใช่`/`ไม่` = เดือนก่อนส่งข้อมูลหรือไม่ ว่างถ้าไม่มีไฟล์เดือนก่อน) เฉพาะเครื่องใน master ที่ยังไม่มีแถวใน `Sheet1`
- ช่องสรุป F1:G4 → เครื่องใน master ทั้งหมด / ส่งข้อมูลแล้ว / ยังไม่ส่งข้อมูล / อัปเดตล่าสุด (`yyyy-MM-dd HH:mm:ss`)

### 4.3 history รายเดือน — `mwd-flow-history-YYYY-MM`

หัวคอลัมน์: `Id`, `ThreadId`, `SerialNumber`, `Status`, `Timestamp` — 1 แถวต่ออีเมล 1 ฉบับ (คีย์ = `Id` ของข้อความ Gmail) ใช้เป็นตัวกัน "ประมวลผลซ้ำ"

### 4.4 Gmail label

`mwd-YYYY-MM` (เช่น `mwd-2026-10`) ติดให้ข้อความที่มีสถานะ `COMPLETE` และ `SUPERSEDED` เท่านั้น

---

## 5. Workflow `02_create_files_mwd` (สร้างไฟล์/label รายเดือน)

**ทางเข้า (trigger)**
1. เรียกจาก `01_counter_mwd` ทุกรอบ (ตัวหลัก)
2. Schedule Trigger วันที่ 5 ของเดือน 00:00 (cron `0 0 5 * *`, ตัวสำรอง)
3. Manual Trigger

**ขั้นตอน**
1. **Build Specs** — กำหนดไฟล์ที่ต้องมีของเดือนนี้ (`$now` รูป `yyyy-MM`) *จุดแก้ไขเดียว*
   - `mwd-YYYY-MM`: หัวตาราง 9 คอลัมน์ (machineDate, serialNumber, machineModel, unit, building, previousMonth, totalCounter, diff, remaining), **ต้องมี label**
   - `mwd-flow-history-YYYY-MM`: หัวตาราง 5 คอลัมน์ (Id, ThreadId, SerialNumber, Status, Timestamp), ไม่มี label
   - สร้าง request body ของ Sheets API พร้อมสไตล์หัวตาราง (ตัวหนา, กึ่งกลาง, เส้นขอบ) และแท็บชื่อ `Sheet1` (sheetId 0)
2. **Search Drive** — ค้นไฟล์ด้วยชื่อ
3. **Check Exists** — ตรวจว่าแต่ละไฟล์มีอยู่แล้วหรือไม่ (นับเฉพาะ mimeType = Google Spreadsheet) แล้วแยกเป็น 2 สาย
4. **สาย A (ไฟล์)**: `Needs File` (เฉพาะ `exists=false`) → `Create Spreadsheet` (POST `sheets.googleapis.com/v4/spreadsheets` สร้างไฟล์ + หัวตาราง ในครั้งเดียว)
5. **สาย B (label)**: `Label Specs` (เฉพาะสเปคที่ `label=true`) → `Get Labels` (ดึง label ทั้งหมดใน Gmail) → `Need Label` (เฉพาะที่ยังไม่มี) → `Create Label`

ทุก node ที่เรียก API มี retry 3 ครั้ง (รอ 5 วินาที) · **ห้ามเปลี่ยนชื่อไฟล์ / แท็บ `Sheet1` / หัวคอลัมน์**

---

## 6. Workflow `01_counter_mwd` (อ่านอีเมล → บันทึกข้อมูล)

### 6.1 ทางเข้า

| Trigger | ความถี่ | พฤติกรรม |
|---|---|---|
| `Gmail Trigger` | poll ทุก 1 นาที (filter: sender) | ไปที่ `Collect IDs` ทันที (ข้าม `List Month Emails`) |
| `Daily Sweep` | cron `0 * * * *` (**ทุกต้นชั่วโมง** แม้ชื่อว่า Daily) | ค้นอีเมลตั้งแต่ต้นเดือนมาเก็บตก |
| `Manual Trigger` | กดเอง | **dry-run เสมอ** (ไม่เขียนข้อมูล) เว้นแต่ตั้ง `forceReal = true` |

### 6.2 ขั้นตอนโดยละเอียด

1. **List Month Emails** — `GET gmail/v1/users/me/messages?q=from:pachara.l@mwa.co.th after:<epoch ต้นเดือน>&maxResults=500` (retry 3 ครั้ง)
2. **Collect IDs** — รวมรายการ `{id, threadId}` ตัดซ้ำ ถ้าไม่มีอีเมลเลยส่ง `{noEmails:true}` ต่อไป เพื่อให้ flow ยังสร้างไฟล์และอัปเดต `missing` ได้
3. **Create Files** — Execute Workflow `02_create_files_mwd` (รอให้เสร็จ, `onError: continueRegularOutput` → ถ้าล้มเหลวก็ไปต่อ)
4. **Build Names** — ★ **CONFIG อยู่ที่ node นี้** แล้วสร้างรายชื่อไฟล์ 3 รายการ (main / history / prev)
   ```js
   CONFIG = {
     masterSheetId: '1GreO344YHG2ztriQTMtp2giJVizu6lGqNOJLtnll60U',
     mainPrefix: 'mwd',
     historyPrefix: 'mwd-flow-history',
     forceReal: false,  // true = รัน Manual แล้วเขียนจริง
     reprocess: false   // true = ข้าม history ประมวลผลอีเมลเดือนนี้ใหม่ทั้งหมด
   }
   ym = เดือนปัจจุบัน (yyyy-MM), prevYm = เดือนก่อน
   dryRun = ($execution.mode === 'test') && !forceReal
   ```
5. **Search Drive → Resolve Files** — หา file ID ด้วยชื่อ (เฉพาะ Google Spreadsheet)
   - ไม่พบไฟล์ main หรือ history → **throw error หยุด flow**
   - ไม่พบไฟล์เดือนก่อน → ไปต่อ แต่ `previousMonth`/`diff` จะว่าง
6. **อ่านข้อมูล 4 ชุด** (ตามลำดับ): `Read History` (A:E) → `Read Master` → `Read Previous` (A:I, ล้มเหลวได้) → `Read Main` (A:I)
7. **Pick New IDs → Has New IDs?** — ตัดอีเมลที่ history มีสถานะขึ้นต้นด้วย `COMPLETE|SKIPPED|SUPERSEDED` ออก (สถานะ `ERROR_*` จะถูกลองใหม่ทุกรอบ) · ถ้าไม่มีอีเมลใหม่ → ข้ามไป `Summary` (และสาขา missing) · `reprocess=true` ข้ามการกรองนี้
8. **Get a message** — ดึงเนื้อหาอีเมลเต็มทีละฉบับ (`simple:false`, retry 3 ครั้ง)
9. **Parse + Compute** — หัวใจของ flow (ดูหัวข้อ 7)
10. **Dry run?** — ถ้า dry-run ข้ามไป `Summary` ไม่เขียนอะไรเลย
11. **Has Main Rows? → Main Rows → Write Main** — เขียนแถว `COMPLETE` ลง `Sheet1` ของไฟล์ main แบบ `appendOrUpdate` โดยจับคู่ด้วย `serialNumber` (ถ้าไม่มีแถว `COMPLETE` ข้ามไปเขียน history เลย)
12. **History Rows → Write History** — เขียนทุกอีเมลที่ประมวลผล (ทุกสถานะ) ลงไฟล์ history แบบ `appendOrUpdate` จับคู่ด้วย `Id`
13. **Get Labels → Plan Labels → Label Needed? → Add Label** — หา label `mwd-YYYY-MM` แล้วติดให้ข้อความ `COMPLETE` + `SUPERSEDED` ทีละข้อความ (ถ้าไม่พบ label จะไม่ติด และบันทึกเป็น note)
14. **Summary** — นับจำนวนตามสถานะ รวมรายการ `ERROR_*`/`SKIPPED_*` และ notes → `hasIssues`
15. **Any Issues? → Alert (choose channel)** — มีปัญหาและไม่ใช่ dry-run จะไป Alert **แต่ node นี้ยังเป็น NoOp (placeholder) — ปัจจุบันไม่มีการแจ้งเตือนจริง**
16. **สาขา missing** (ทำทุกรอบหลัง Summary ขนานกับ Any Issues?):
    `Read Main Fresh` → `Compute Missing` → `Write Missing?` (เฉพาะไม่ใช่ dry-run) → `Sheet List` → `Need Missing Sheet` → `Create Sheet?` → `Add Sheet` (ถ้ายังไม่มีแท็บ `missing`) → `Clear Missing` (`missing!A:Z:clear`) → `Write Missing` (`values:batchUpdate` ที่ `A1` และ `F1`) → `Build Format` → `Apply Format` (หัวตารางตัวหนา/กลาง/เส้นขอบ + auto-resize คอลัมน์)

### 6.3 แผนผังสรุป

```
Gmail Trigger ───────────────┐
Daily Sweep ─┐               ▼
Manual ──────┴─ List Month Emails ─► Collect IDs ─► Create Files (02_create_files_mwd)
                                                        │
        Build Names ─► Search Drive ─► Resolve Files ─► Read History/Master/Previous/Main
                                                        │
                                   Pick New IDs ─► Has New IDs? ──no──► Summary
                                                        │yes
                    Get a message ─► Parse + Compute ─► Dry run? ──yes──► Summary
                                                        │no
        Write Main ─► Write History ─► Get Labels ─► Plan Labels ─► Add Label ─► Summary
                                                                            ├─► Any Issues? ─► Alert(NoOp)
                                                                            └─► Read Main Fresh ─► … ─► sheet `missing`
```

---

## 7. กติกาธุรกิจใน `Parse + Compute`

ลำดับการตัดสินใจต่ออีเมล 1 ฉบับ:

1. ไม่พบ serial → `ERROR_NO_SERIAL`
2. อ่านวันที่ไม่ได้ → `ERROR_PARSE_DATE`
3. เดือนของวันที่ในอีเมล ≠ เดือนที่ประมวลผล → `SKIPPED_OTHER_MONTH`
4. serial ไม่มีใน master → `ERROR_NO_MASTER`
5. อื่น ๆ → `COMPLETE` พร้อมแถวผลลัพธ์

จากนั้นตัดสิน `SUPERSEDED` (ไม่เขียนลงชีต):
- ในชุดอีเมลรอบนี้ เครื่องเดียวกันมีหลายฉบับ → เก็บฉบับที่ **วันที่ใหม่สุด** ฉบับอื่นเป็น `SUPERSEDED`
- ถ้าใน `Sheet1` มีแถวของเครื่องนี้อยู่แล้วและวันที่ **ใหม่กว่า** อีเมลที่กำลังประมวลผล → `SUPERSEDED` (ยกเว้น `reprocess=true`)

| สถานะ | ความหมาย | เขียน Sheet1 | ติด label | ถูกข้ามในรอบถัดไป |
|---|---|---|---|---|
| `COMPLETE` | ข้อมูลครบ อยู่ในเดือนนี้ | ใช่ | ใช่ | ใช่ |
| `SUPERSEDED` | มีข้อมูลใหม่กว่าแล้ว | ไม่ | ใช่ | ใช่ |
| `SKIPPED_OTHER_MONTH` | วันที่ไม่ตรงเดือนนี้ | ไม่ | ไม่ | ใช่ |
| `ERROR_NO_SERIAL` / `ERROR_PARSE_DATE` / `ERROR_NO_MASTER` | ข้อมูลผิดปกติ/ไม่อยู่ใน master | ไม่ | ไม่ | **ไม่ (ลองใหม่ทุกรอบ)** |

**สูตรคำนวณ**
- `previousMonth` = `totalCounter` ของ serial เดียวกันในไฟล์เดือนก่อน (ถ้าเครื่องนั้นไม่มีแถวในไฟล์เดือนก่อน → `0`)
- ถ้าไม่มีไฟล์เดือนก่อน หรือไฟล์ว่าง → `previousMonth` และ `diff` เป็นค่าว่าง และมี note `previous month file missing or empty`
- `diff = totalCounter − previousMonth`
- `remaining` = ตัวเลข toner สีแรก + `%`

**ข้อควรรู้**
- ทำงานระดับ "ข้อความ" (message id) ไม่แตะ thread ไม่ลบอีเมล
- idempotent: รันซ้ำกี่รอบก็ได้ผลเท่าเดิม เพราะกรองด้วย history และเขียนแบบ upsert
- รอบแรกของเดือน ไฟล์ใหม่ยังว่าง → sheet `missing` จะแสดงว่าทุกเครื่องยังไม่ส่ง

---

## 8. ข้อสังเกตและข้อจำกัดที่ทราบ

1. **Alert ยังไม่ทำงานจริง** — node `Alert (choose channel)` เป็น NoOp ปัญหา (`ERROR_*`) จะเห็นได้เฉพาะใน history/ผลการรัน
2. **Drive ไม่ถูกจัดเข้า folder อัตโนมัติ** — ไฟล์ใหม่ไปอยู่ root (ต่างจาก oag)
3. **ไม่มีการไฮไลท์แถวผิดปกติ** — ชุด mwd ไม่มีฟีเจอร์ระบายแดงเมื่อเครื่องไม่มีในไฟล์เดือนก่อน (มีเฉพาะ oag)
4. ไฟล์เดือนก่อนไม่มีเครื่องนั้น → `previousMonth = 0` (diff = totalCounter) แต่ไม่ได้ flag ต่างจากกรณีไม่มีไฟล์เดือนก่อนเลย (ปล่อยว่าง)
5. ค่า toner ใช้เฉพาะสีแรกในอีเมล (ปกติคือ Black) — ถ้าต้องการทุกสีต้องแก้ parser และเพิ่มคอลัมน์
6. query `after:` ใช้ต้นเดือนตามเวลาของ n8n (`$now`) ขอบเดือนอาจคลาดเคลื่อนตาม timezone ของ instance; ไม่ได้ใส่ `before:` (ต่างจาก oag)
7. จำกัด 500 อีเมลต่อรอบ (`maxResults`) — พอสำหรับ 119 เครื่อง/เดือน
8. ไฟล์ `mwd-2025-11` ไม่มี history คู่กัน (history เริ่ม `2025-12`) เป็นข้อมูลก่อนเริ่มใช้ flow รุ่นปัจจุบัน
9. Credential ที่ใช้: Gmail OAuth2, Google Drive, Google Sheets OAuth2 (ผูกกับบัญชีเจ้าของ n8n)

---

## 9. แนวทางย้ายจาก n8n → Claude

### 9.1 การจับคู่ส่วนประกอบ

| ใน n8n | ใน Claude | เหตุผล |
|---|---|---|
| `Daily Sweep` (cron ทุกชั่วโมง) | **Scheduled task** (ทุกชั่วโมง `0 * * * *` — ขั้นต่ำของระบบคือรายชั่วโมง พอดีกับของเดิม) | ตัวกระตุ้นตามเวลา |
| `Gmail Trigger` (ทุก 1 นาที) | **ตัดทิ้ง** — ให้ sweep รายชั่วโมงทำหน้าที่แทน | Claude ไม่มี push จากอีเมล; sweep เดิมเก็บตกครบอยู่แล้ว ความหน่วงเพิ่มสูงสุด ~1 ชม. |
| `Manual Trigger` (dry-run) | **Skill** `counter-sync` สั่งรันเองด้วย `--dry-run` | ใช้ทดสอบ/ตรวจสอบ |
| `Code` nodes (`Parse + Compute`, `Compute Missing`, `Plan Labels` ฯลฯ) | **สคริปต์ Python** (parse, compute, missing) + unit test | logic ตายตัว ไม่ควรให้ LLM คำนวณทุกรอบ |
| `Gmail` nodes (list / get / label) | Gmail connector (`search_threads`, `get_message`, `label_message`, `create_label`) หรือ Gmail API ในสคริปต์ | ระดับข้อความ (message id) เหมือนเดิม |
| `Google Drive` / `Google Sheets` nodes | connector ของ Drive/Sheets หรือ Google API (service account) ในสคริปต์ — **หรือ** เปลี่ยนมาใช้ไฟล์ `.xlsx` ในโฟลเดอร์นี้เป็นแหล่งข้อมูลหลัก | ต้องตัดสินใจว่า "แหล่งจริง" คืออะไร (ดู 9.3) |
| `02_create_files_mwd` | Skill/ฟังก์ชัน `ensure-monthly-files` ที่ `counter-sync` เรียกก่อนทุกครั้ง | คงพฤติกรรม "idempotent, สร้างถ้ายังไม่มี" |
| `Alert (choose channel)` | แจ้งเตือนจริง (push / ร่างอีเมล) เมื่อมี `ERROR_*` | ของเดิมยังไม่ทำงาน — โอกาสปรับปรุง |
| `Build Names` CONFIG | ไฟล์ config (เช่น `config.yaml`) ข้างสคริปต์ | จุดแก้ไขเดียวเหมือนเดิม |
| History sheet | คงไว้ (ใช้เป็น idempotency key) | หัวใจกันประมวลผลซ้ำ |

### 9.2 Hooks — ใช้เป็น guardrail ไม่ใช่ trigger

Hooks ของ Claude ทำงานเมื่อเกิดเหตุการณ์ **ภายใน session** (ก่อน/หลังเรียกเครื่องมือ, เริ่ม session, ส่ง prompt, หยุดตอบ) **ไม่ใช่เมื่ออีเมลเข้า หรือเมื่อถึงเวลา** จึงใช้แทน Gmail Trigger/cron ไม่ได้ ที่เหมาะคือ:
- `PreToolUse`: บล็อกการเขียนตรงเข้า `02_historys/` และ `03_report_files/` ถ้าไม่ได้ผ่านสคริปต์ที่กำหนด
- `PostToolUse`: ตรวจหัวคอลัมน์/จำนวนคอลัมน์หลังเขียนไฟล์ (9 คอลัมน์ report, 5 คอลัมน์ history)
- `SessionStart`: สรุปสถานะเดือนนี้ (จำนวนส่งแล้ว/ยังไม่ส่ง, error ค้าง)

### 9.3 ข้อควรตัดสินใจก่อนถอด n8n

1. **แหล่งข้อมูลจริงอยู่ที่ไหน** — ถ้าคนอื่นยังเปิดดู Google Sheets อยู่ ต้องให้ Claude เขียนกลับ Sheets (ไม่ใช่แค่ xlsx ในเครื่อง) ไม่เช่นนั้นสองที่จะไม่ตรงกัน
2. **ต้นทุน** — scheduled task แต่ละรอบเป็น session ใหม่ที่เรียก LLM; ควรให้สคริปต์เช็ค "มีอีเมลใหม่ไหม" ก่อน (fast path) ถ้าไม่มีให้จบทันที
3. **Session ใหม่ทุกรอบไม่มีความจำ** — prompt ของ scheduled task ต้องบอกครบ (path สคริปต์, config, โหมด dry-run/จริง)
4. **การอนุมัติ** — รันไม่มีคนเฝ้า การเขียนข้อมูลจะต้องตั้งสิทธิ์ให้ทำงานได้โดยไม่ต้องรออนุมัติ
5. **Sweep รายชั่วโมงเดียวพอ** — ความหน่วงสูงสุด ~1 ชม. ถ้ายอมรับได้ก็ไม่ต้องมีตัวแทน Gmail Trigger
6. คงพฤติกรรม **dry-run เป็นค่าเริ่มต้นสำหรับการรันมือ**

### 9.4 โครงที่แนะนำ

```
.claude/skills/counter-sync/SKILL.md     # วิธีรัน, dry-run, ตรวจผล, แก้ error
scripts/counter/
  config.yaml                            # master id, prefix, sender, flags
  parse_email.py                         # regex ตามหัวข้อ 3
  compute.py                             # กติกาหัวข้อ 7 (สถานะ, diff, superseded)
  missing.py                             # คำนวณ sheet missing
  run.py --dry-run | --reprocess         # ประสานงาน: ensure files → read → compute → write
tests/                                   # อีเมลตัวอย่าง + ผลที่คาดหวังของทุกสถานะ
```

### 9.5 Checklist ก่อนปิด n8n

- [ ] รัน dry-run ของระบบใหม่เทียบกับผลของ n8n ในเดือนเดียวกัน (ผลต้องตรงทุกแถว)
- [ ] ทดสอบทุกสถานะ: `COMPLETE`, `SUPERSEDED`, `SKIPPED_OTHER_MONTH`, `ERROR_*`
- [ ] ทดสอบกรณีไม่มีไฟล์เดือนก่อน / เครื่องไม่มีในเดือนก่อน / ไม่มีอีเมลใหม่
- [ ] ทดสอบรอยต่อขึ้นเดือนใหม่ (สร้างไฟล์ + label อัตโนมัติ)
- [ ] ตั้ง Alert จริงสำหรับ `ERROR_*`
- [ ] ปิด (ไม่ลบ) workflow n8n ทั้ง 2 ตัวไว้ก่อนช่วงทดลองคู่ขนาน แล้วค่อยลบ
- [ ] ป้องกันสองระบบเขียนทับกัน — ห้ามเปิดทั้ง n8n และระบบใหม่พร้อมกันในโหมดเขียนจริง

---

# ส่วนที่ 2: สตง. (oag)

# 02_สตง — ระบบเก็บ Counter เครื่องถ่ายเอกสาร (สำนักงานการตรวจเงินแผ่นดิน / สตง. / OAG)

เอกสารนี้อธิบายการทำงานของชุด workflow **oag** ใน n8n (project `os9TBq7Y6zz7S0Iy`) ที่อ่านอีเมลรายงานเครื่องถ่ายเอกสาร → สกัดข้อมูล → คำนวณ → บันทึกลง Google Sheet รายเดือน
เขียนขึ้นเพื่อใช้เป็นต้นแบบในการถอด n8n ออกแล้วย้ายไปเป็น skills / scheduled task / hooks ของ Claude (ดูหัวข้อ 9)

> อ้างอิงจากการอ่าน workflow จริง ณ วันที่ 12 ต.ค. 2026 (workflow สร้างเมื่อ 10 ต.ค. 2026 โดยเลียนแบบชุด mwd แล้วพัฒนาต่อ)
> ไฟล์ `.xlsx` ในโฟลเดอร์นี้เป็นสำเนาที่ export จาก Google Sheets — **แหล่งข้อมูลจริงของ flow อยู่ใน Google Drive** ไม่ใช่โฟลเดอร์นี้

---

## 1. ภาพรวม

- เครื่องถ่ายเอกสาร Toshiba ของ สตง. ส่งอีเมลรายงานอัตโนมัติ (1 อีเมล = 1 เครื่อง) มาจากผู้ส่ง **`networkservice@oag.go.th`**
- Flow อ่านอีเมลเหล่านั้น แกะค่า Date / Model / Serial / Total Counter / Toner% แล้วเทียบกับ master (เครื่อง → หน่วยงาน, อาคาร)
- คำนวณส่วนต่างจากเดือนก่อน (`diff = totalCounter − previousMonth`) แล้วเขียนลงไฟล์รายเดือน `oag-YYYY-MM`
- เครื่องที่ **ไม่มีในไฟล์เดือนก่อน** จะถูกระบายพื้นหลังแดงทั้งแถว เป็นธงให้คนตรวจ (ไม่ลบอัตโนมัติ)
- ติด Gmail label `oag-YYYY-MM` ให้อีเมลที่ประมวลผลแล้ว
- เขียน sheet `missing` ในไฟล์เดือนนั้นทุกรอบ เพื่อบอกว่าเครื่องไหนใน master **ยังไม่ส่งข้อมูล**
- มี 2 workflow ที่ทำงานคู่กัน:

| Workflow | ID | หน้าที่ |
|---|---|---|
| `02_create_files_oag` | `wJaGZVr0Ju0BYkOL` | สร้างไฟล์ Google Sheet + Gmail label ของเดือนปัจจุบัน แล้ว **ย้ายเข้า folder ที่ถูกต้อง** (รันซ้ำได้ปลอดภัย) |
| `01_counter_oag` | `k25MRGHanXGwfw2n` | อ่านอีเมล → คำนวณ → เขียนข้อมูล → ไฮไลท์ → ติด label → อัปเดต sheet `missing` |

`01_counter_oag` เรียก `02_create_files_oag` ก่อนทุกรอบ (รอจนเสร็จ) เพื่อให้ไฟล์เดือนใหม่ถูกสร้างตั้งแต่รอบแรกของเดือน

---

## 2. โครงสร้างโฟลเดอร์

```
02_สตง/
├── README.md
├── 01_master/
│   └── master_oag.xlsx                  # ข้อมูลเครื่อง: machine(serial) → unit, building
├── 02_historys/
│   └── oag-flow-history-YYYY-MM.xlsx    # log การประมวลผลอีเมลรายเดือน (กันทำซ้ำ)
└── 03_report_files/
    └── oag-YYYY-MM.xlsx                 # รายงานรายเดือน (Sheet1 = ข้อมูล, missing = เครื่องที่ยังไม่ส่ง)
```

โครงสร้างนี้ตรงกับ Google Drive จริง (My Drive > 02_สตง) — flow `02_create_files_oag` ย้ายไฟล์เข้าสอง folder นี้ให้อัตโนมัติโดยอ้างด้วย **Folder ID**:

| Folder | Folder ID | ใช้กับ |
|---|---|---|
| `03_report_files` | `1tK7u1MzrG1emmfKgBVnkofkUZpkKYxnd` | ไฟล์ `oag-YYYY-MM` |
| `02_historys` | `1J554kbttMoMF0M7IeujapUW7KXg5KubS` | ไฟล์ `oag-flow-history-YYYY-MM` |

ณ ปัจจุบันมีข้อมูลของเดือน `2026-10` เดือนเดียว (ยังไม่มีอีเมลที่ประมวลผล — `Sheet1` ว่าง และ `missing` แสดงว่า 37 เครื่องยังไม่ส่ง)

---

## 3. ข้อมูลต้นทาง: อีเมลรายงานเครื่อง

- ผู้ส่ง: `networkservice@oag.go.th` (ตั้งไว้ 2 จุด: node `Gmail Trigger` > Filters > Sender และ `CONFIG.sender` ใน node `Build Names`)
- รูปแบบเนื้อหาเหมือนชุด mwd (plain text):

```
Date : 28-09-2026 10:39
Machine Model : TOSHIBA e-STUDIO...
Serial Number : CTAR33988
Total Counter : 123456
Toner Information
Black   4
...
```

Regex ที่ใช้แกะ (node `Parse + Compute`):

| ฟิลด์ | Pattern |
|---|---|
| `machineDate` | `/Date\s*:\s*(.*)/` |
| `machineModel` | `/Machine Model\s*:\s*(.*)/` |
| `serialNumber` | `/Serial Number\s*:\s*(\S+)/` (ใช้ token แรกก่อนช่องว่าง) |
| `totalCounter` | `/Total Counter\s*:\s*(\d+)/` |
| toner | อ่านส่วนหลังคำว่า `Toner Information` ด้วย `/(Black\|Cyan\|Magenta\|Yellow)\s+(\d+)/g` — **ใช้เฉพาะสีแรก (`toner[0]`)** มาเป็น `remaining` เช่น `4%` |

การอ่านวันที่ (`parseDate`) รองรับ: `yyyy-MM-dd[ HH:mm]`, `dd-MM-yyyy[ HH:mm]` (ถ้าเดือน > 12 และวัน ≤ 12 จะสลับให้), ตัวเลข serial ของ Excel — ตีความเป็น UTC ตามที่เขียนในอีเมล (ไม่แปลง timezone) แล้วเก็บเป็นข้อความรูป `dd-MM-yyyy HH:mm`

---

## 4. โครงสร้างข้อมูล (Schema)

### 4.1 master — `master_oag` (Google Sheet ID `17Sa3SUsaNcHqoVhblrgKOHeYir0_XDS9t__vwZB4UpA`)

| คอลัมน์ | ความหมาย |
|---|---|
| `unit` | ชื่อหน่วยงาน |
| `machine` | Serial Number ของเครื่อง (คีย์ที่ใช้จับคู่กับอีเมล) |
| `building` | อาคาร/ชั้น/ที่ตั้ง |

ปัจจุบันมีเครื่อง **37 เครื่อง** · serial ซ้ำใน master นับครั้งเดียว · ค่าในช่อง `machine` ที่ไม่ใช่ serial (เช่น "รอเครื่องเข้า") จะค้างในรายการ "ยังไม่ส่ง" จนกว่าจะแก้ master

### 4.2 report รายเดือน — `oag-YYYY-MM`

**แท็บ `Sheet1`** (ห้ามเปลี่ยนชื่อแท็บ/ชื่อหัวคอลัมน์ เพราะ flow อ้างอิงด้วยชื่อ) — คีย์ของแถวคือ `serialNumber` (คอลัมน์ B)

| คอลัมน์ | ที่มา |
|---|---|
| `machineDate` | วันที่ในอีเมล รูป `dd-MM-yyyy HH:mm` (เขียนนำหน้าด้วย `'` ให้ Sheets เก็บเป็นข้อความ) |
| `serialNumber` | จากอีเมล |
| `machineModel` | จากอีเมล |
| `unit` / `building` | จาก master |
| `previousMonth` | `totalCounter` ของเครื่องเดียวกันในไฟล์เดือนก่อน (`0` ถ้าไม่มี) |
| `totalCounter` | จากอีเมล |
| `diff` | `totalCounter − previousMonth` |
| `remaining` | % toner (สีแรก) |

**แท็บ `missing`** — สร้างและเขียนทับโดย flow (อ่านอย่างเดียว อย่าแก้ด้วยมือ)

- ตาราง A:D → `unit`, `machine`, `building`, `reportedLastMonth` (`ใช่`/`ไม่` = เดือนก่อนส่งข้อมูลหรือไม่ ว่างถ้าไม่มีไฟล์เดือนก่อน) เฉพาะเครื่องใน master ที่ยังไม่มีแถวใน `Sheet1`
- ช่องสรุป F1:G4 → เครื่องใน master ทั้งหมด / ส่งข้อมูลแล้ว / ยังไม่ส่งข้อมูล / อัปเดตล่าสุด (`yyyy-MM-dd HH:mm:ss`)

### 4.3 history รายเดือน — `oag-flow-history-YYYY-MM`

หัวคอลัมน์: `Id`, `ThreadId`, `SerialNumber`, `Status`, `Timestamp` — 1 แถวต่ออีเมล 1 ฉบับ (คีย์ = `Id` ของข้อความ Gmail) ใช้เป็นตัวกัน "ประมวลผลซ้ำ"

### 4.4 Gmail label

`oag-YYYY-MM` ติดให้ข้อความที่มีสถานะ `COMPLETE` และ `SUPERSEDED` เท่านั้น

---

## 5. Workflow `02_create_files_oag` (สร้าง + ย้ายไฟล์ + label รายเดือน)

**ทางเข้า (trigger)**
1. เรียกจาก `01_counter_oag` ทุกรอบ (Execute Workflow)
2. Schedule Trigger วันที่ 5 ของเดือน 00:00 (cron `0 0 5 * *`)
3. Manual Trigger

**CONFIG (node `Build Specs` — แก้ที่เดียว)**

| คีย์ | ความหมาย |
|---|---|
| `env` | `'prod'` = ไฟล์จริง · `'test'` = โฟลเดอร์ทดลอง (prefix `zz-test-oag`, ต้องกรอก `test.mainFolderId` / `test.historyFolderId` ก่อน) |
| `dryRun` | `true` = แสดงแผนอย่างเดียว (ไม่สร้าง/ย้าย/สร้าง label) · `false` = ทำจริง |
| `testYm` | ว่าง = เดือนปัจจุบัน · `'YYYY-MM'` = จำลองเดือนอื่น (ทดสอบเท่านั้น ต้องคืนเป็นว่างก่อนใช้งานจริง) |
| `prod.prefix` | `oag` |
| `prod.mainFolderId` / `prod.historyFolderId` | ID ของ `03_report_files` / `02_historys` (อ้างด้วย ID เพราะชื่อเปลี่ยนหรือซ้ำได้) |

**ขั้นตอน**
1. **Build Specs** — สร้างสเปค 2 ไฟล์
   - `oag-YYYY-MM`: หัวตาราง 9 คอลัมน์, **ต้องมี label**, folder = `03_report_files`
   - `oag-flow-history-YYYY-MM`: หัวตาราง 5 คอลัมน์, ไม่มี label, folder = `02_historys`
   - พร้อม request body ของ Sheets API (หัวตารางตัวหนา กึ่งกลาง เส้นขอบ, แท็บ `Sheet1`)
2. **Search Drive** — ค้นไฟล์ตามชื่อ โดยขอข้อมูล `parents` กลับมาด้วย (`fields: ["*"]`)
3. **Check Exists** — เทียบกับ folder ปลายทาง (ไม่นับไฟล์ที่อยู่ในถังขยะ) แยกสถานะ:
   - `ok` — มีและอยู่ถูก folder → ข้าม
   - `misplaced` — มีแต่อยู่ผิด folder → ย้ายอย่างเดียว
   - `missing` — ยังไม่มี → สร้างแล้วย้าย
4. **Dry run?** — ถ้า dryRun → `Dry Run Plan` (แสดงแผนว่าไฟล์ไหนจะ skip / move / create+move และ label ที่จะสร้าง) แล้วจบ · ถ้าไม่ใช่ แยกเป็น 3 สายขนานกัน

**สาย A — สร้างไฟล์ใหม่**: `Needs File` (state = missing) → `Create Spreadsheet` (POST Sheets API; สร้างลง folder โดยตรงไม่ได้ จึงสร้างที่ root ก่อน) → `Move New File` (ย้ายเข้า folder ของไฟล์นั้น)

**สาย B — ย้ายไฟล์ที่อยู่ผิดที่**: `Needs Move` (state = misplaced) → `Move Existing File` (ไม่สร้างซ้ำ)

**สาย C — label**: `Label Specs` (เฉพาะ main) → `Get Labels` → `Need Label` (เฉพาะที่ยังไม่มี) → `Create Label` (`oag-YYYY-MM`)

**การกู้คืน**: ถ้าสร้างสำเร็จแต่ย้ายไม่สำเร็จ ไฟล์จะค้างที่ root และ flow error — แก้สาเหตุแล้วรันใหม่ ระบบจะย้ายไฟล์เดิมให้ (สถานะ `misplaced`) ไม่สร้างซ้ำ

ทุก node ที่เรียก API มี retry 3 ครั้ง (รอ 5 วินาที) · **ห้ามเปลี่ยนชื่อไฟล์ / แท็บ `Sheet1` / หัวคอลัมน์**

---

## 6. Workflow `01_counter_oag` (อ่านอีเมล → บันทึกข้อมูล)

### 6.1 ทางเข้า

| Trigger | ความถี่ | พฤติกรรม |
|---|---|---|
| `Gmail Trigger` | poll ทุก 1 นาที (filter: sender) | ใช้ข้อความจาก trigger โดยตรง ข้าม `List Month Emails` |
| `Daily Sweep` | cron `0 * * * *` (**ทุกต้นชั่วโมง** แม้ชื่อว่า Daily) | ค้นอีเมลทั้งเดือนมาเก็บตก |
| `Manual Trigger` | กดเอง | ทำงานตาม `CONFIG.dryRun` (ต่างจาก mwd ที่ dry-run เสมอ) |

### 6.2 CONFIG (node `Build Names` — แก้ที่เดียว)

| คีย์ | ค่าปัจจุบัน | ความหมาย |
|---|---|---|
| `env` | `'prod'` | `'prod'` = ไฟล์จริง (prefix `oag`) · `'test'` = ทดสอบ (prefix `zz-test-oag` ต้องมีไฟล์ที่ flow 02 สร้างไว้ก่อน) |
| `dryRun` | `false` | `true` = อ่านอย่างเดียว ไม่เขียน sheet / ไม่ไฮไลท์ / ไม่ติด label |
| `testYm` | `''` | ว่าง = เดือนปัจจุบัน · `'YYYY-MM'` = จำลองเดือนอื่น (ใช้ได้เฉพาะ env test) |
| `reprocess` | `false` | `true` = ข้าม history ประมวลผลอีเมลทุกฉบับของเดือนนั้นใหม่ (ทดสอบเท่านั้น) |
| `sender` | `networkservice@oag.go.th` | ต้องตรงกับ Gmail Trigger > Filters > Sender |
| `masterSheetId` | `17Sa3SUsaNcHqoVhblrgKOHeYir0_XDS9t__vwZB4UpA` | master_oag |
| `flagColor` | `{red:1, green:0.4, blue:0.4}` | สีพื้นแถวที่ไม่มีข้อมูลเดือนก่อน |

Build Names คำนวณ `ym`, `prevYm`, และช่วงค้นอีเมล `afterSec` (ต้นเดือน) – `beforeSec` (ต้นเดือนถัดไป) แล้วสร้างรายการชื่อไฟล์ 3 รายการ (main / history / prev)

### 6.3 ขั้นตอนโดยละเอียด

1. **Build Names** — ตามข้างบน
2. **Via Email Trigger?** — ถ้ามาจาก Gmail Trigger → `Collect IDs` ตรง ๆ · ถ้ามาจาก Sweep/Manual → `List Month Emails` ก่อน
3. **List Month Emails** — `GET gmail/v1/users/me/messages?q=from:<sender> after:<afterSec> before:<beforeSec>&maxResults=500` (retry 3 ครั้ง)
4. **Collect IDs** — รวมรายการ `{id, threadId}` ตัดซ้ำ ถ้าไม่มีอีเมลเลยส่ง `{noEmails:true}` ต่อไป เพื่อให้ flow ยังสร้างไฟล์และอัปเดต `missing` ได้
5. **Create Files** — Execute Workflow `02_create_files_oag` (รอให้เสร็จ, `onError: continueRegularOutput`)
6. **Names → Search Drive → Resolve Files** — หา file ID ของ main / history / เดือนก่อน (เฉพาะ Google Spreadsheet)
   - ไม่พบ main หรือ history → **throw error หยุด flow**
   - ไม่พบเดือนก่อน → ถือว่า `previousMonth = 0`
7. **อ่านข้อมูล 4 ชุด**: `Read History` (A:E) → `Read Master` → `Read Previous` (A:I, ล้มเหลวได้) → `Read Main` (A:I)
8. **Pick New IDs → Has New IDs?** — ตัดอีเมลที่ history ขึ้นต้นด้วย `COMPLETE|SKIPPED|SUPERSEDED` (สถานะ `ERROR_*` ถูกลองใหม่ทุกรอบ) · ไม่มีอีเมลใหม่ → ข้ามไป `Summary` (และสาขา missing)
9. **Get a message** — ดึงเนื้อหาอีเมลเต็มทีละฉบับ
10. **Parse + Compute** — หัวใจของ flow (หัวข้อ 7)
11. **Dry run?** — ถ้า dryRun → `Summary` ไม่เขียนอะไร
12. **Has Main Rows? → Main Rows → Write Main** — เขียนแถว `COMPLETE` ลง `Sheet1` แบบ `appendOrUpdate` จับคู่ด้วย `serialNumber`
13. **Flag Rows? → Read Serial Column → Build Highlight → Apply Highlight** — ถ้ามีเครื่องติดธง: อ่านคอลัมน์ B (`Sheet1!B:B`) หาเลขแถวของ serial ที่ติดธง แล้วส่ง `batchUpdate repeatCell` ระบายพื้นแดงคอลัมน์ A–I ทั้งแถว
    - ถ้าหาแถวไม่พบ → throw error
    - ถ้าขั้นนี้ล้มเหลว flow จะหยุด **ก่อนเขียน history** → รอบถัดไปประมวลผลอีเมลเดิมซ้ำได้
14. **History Rows → Write History** — เขียนทุกอีเมลที่ประมวลผล (ทุกสถานะ) ลง history แบบ `appendOrUpdate` จับคู่ด้วย `Id`
15. **Get Labels → Plan Labels → Label Needed? → Add Label** — ติด label `oag-YYYY-MM` ให้ข้อความ `COMPLETE` + `SUPERSEDED` (ถ้าไม่พบ label จะไม่ติด และบันทึกเป็น note)
16. **Summary** — นับจำนวนตามสถานะ รวมรายการ `ERROR_*`/`SKIPPED_*`, notes, เครื่องที่ติดธง → `hasIssues`
17. **Any Issues? → Alert (choose channel)** — มีปัญหาและไม่ใช่ dry-run จะไป Alert **แต่ node นี้ยังเป็น NoOp (placeholder) — ปัจจุบันไม่มีการแจ้งเตือนจริง**
18. **สาขา missing** (ทำทุกรอบหลัง Summary ขนานกับ Any Issues?):
    `Read Main Fresh` → `Compute Missing` → `Write Missing?` (เฉพาะไม่ใช่ dry-run) → `Sheet List` → `Need Missing Sheet` → `Create Sheet?` → `Add Sheet` (ถ้ายังไม่มีแท็บ `missing`) → `Clear Missing` → `Write Missing` (A1 และ F1) → `Build Format` → `Apply Format`

### 6.4 แผนผังสรุป

```
Gmail Trigger ─┐
Daily Sweep ───┼─► Build Names ─► Via Email Trigger? ─yes──────────────┐
Manual ────────┘                        │no                            │
                                  List Month Emails ───────────────────┤
                                                                      ▼
                    Collect IDs ─► Create Files (02_create_files_oag: สร้าง+ย้ายไฟล์+label)
                                                                      │
   Names ─► Search Drive ─► Resolve Files ─► Read History/Master/Previous/Main
                                                                      │
                       Pick New IDs ─► Has New IDs? ──no──► Summary
                                                                      │yes
                  Get a message ─► Parse + Compute ─► Dry run? ──yes──► Summary
                                                                      │no
  Write Main ─► Flag Rows? ─yes─► Read Serial Column ─► Build Highlight ─► Apply Highlight ─┐
                        └─no───────────────────────────────────────────────────────────────┤
                                                                                           ▼
                           History Rows ─► Write History ─► Get Labels ─► Plan Labels ─► Add Label ─► Summary
                                                                                             ├─► Any Issues? ─► Alert(NoOp)
                                                                                             └─► Read Main Fresh ─► … ─► sheet `missing`
```

---

## 7. กติกาธุรกิจใน `Parse + Compute`

ลำดับการตัดสินใจต่ออีเมล 1 ฉบับ:

1. ไม่พบ serial → `ERROR_NO_SERIAL`
2. อ่านวันที่ไม่ได้ → `ERROR_PARSE_DATE`
3. เดือนของวันที่ในอีเมล ≠ เดือนที่ประมวลผล → `SKIPPED_OTHER_MONTH`
4. serial ไม่มีใน master → `ERROR_NO_MASTER`
5. อื่น ๆ → `COMPLETE` พร้อมแถวผลลัพธ์

จากนั้นตัดสิน `SUPERSEDED` (ไม่เขียนลงชีต):
- ในชุดอีเมลรอบนี้ เครื่องเดียวกันมีหลายฉบับ → เก็บฉบับที่ **วันที่ใหม่สุด** ฉบับอื่นเป็น `SUPERSEDED`
- ถ้าใน `Sheet1` มีแถวของเครื่องนี้อยู่แล้วและวันที่ **ใหม่กว่า** อีเมลที่กำลังประมวลผล → `SUPERSEDED` (ยกเว้น `reprocess=true`)

| สถานะ | ความหมาย | เขียน Sheet1 | ติด label | ถูกข้ามในรอบถัดไป |
|---|---|---|---|---|
| `COMPLETE` | ข้อมูลครบ อยู่ในเดือนนี้ | ใช่ | ใช่ | ใช่ |
| `SUPERSEDED` | มีข้อมูลใหม่กว่าแล้ว | ไม่ | ใช่ | ใช่ |
| `SKIPPED_OTHER_MONTH` | วันที่ไม่ตรงเดือนนี้ | ไม่ | ไม่ | ใช่ |
| `ERROR_NO_SERIAL` / `ERROR_PARSE_DATE` / `ERROR_NO_MASTER` | ข้อมูลผิดปกติ/ไม่อยู่ใน master | ไม่ | ไม่ | **ไม่ (ลองใหม่ทุกรอบ)** |

### กติกา `previousMonth` / `diff` (ต่างจากชุด mwd)

| กรณี | `previousMonth` | `diff` | ไฮไลท์แดง |
|---|---|---|---|
| ไม่มีไฟล์เดือนก่อน (หรือไฟล์ว่าง) เช่นเดือนแรก | `0` | `totalCounter` | ไม่ |
| มีไฟล์เดือนก่อน **และ** มีเครื่องนี้ | `totalCounter` เดือนก่อน | `totalCounter − previousMonth` | ไม่ |
| มีไฟล์เดือนก่อน แต่ **ไม่มีเครื่องนี้** | `0` | `totalCounter` | **ใช่ ทั้งแถว A–I** (ธงให้คนตรวจ + note ใน Summary) |

- `remaining` = ตัวเลข toner สีแรก + `%`
- ทำงานระดับ "ข้อความ" (message id) ไม่แตะ thread ไม่ลบอีเมล
- idempotent: รันซ้ำกี่รอบก็ได้ผลเท่าเดิม เพราะกรองด้วย history และเขียนแบบ upsert
- รอบแรกของเดือน ไฟล์ใหม่ยังว่าง → sheet `missing` จะแสดงว่าทุกเครื่องยังไม่ส่ง

### ผลการทดสอบที่บันทึกไว้ใน flow (10 ต.ค. 2026, sandbox + อีเมลทดสอบวันที่ 28-09-2026)
ผ่าน: dry-run, เขียนจริง, ข้ามอีเมลที่ประมวลผลแล้ว, ไฮไลท์แดงเครื่องที่ไม่มีในเดือนก่อน, คำนวณ diff เครื่องที่มีในเดือนก่อน, เส้นทาง Gmail Trigger และ Sweep, sheet `missing` (dry-run / เขียนจริง / รันซ้ำ) · `02_create_files_oag` ผ่าน dry-run, สร้างจริง, รันซ้ำไม่ซ้ำ, ย้ายไฟล์ผิดที่, กู้คืนหลังย้ายล้มเหลว และรันจริงบน folder จริง
**ยังไม่ได้ทดสอบ**: กรณี `Apply Highlight` ล้มเหลว และการเขียน `missing` ล้มเหลว

---

## 8. ข้อสังเกตและข้อจำกัดที่ทราบ

1. **Alert ยังไม่ทำงานจริง** — node `Alert (choose channel)` เป็น NoOp ปัญหา (`ERROR_*`) และเครื่องที่ติดธงจะเห็นได้เฉพาะใน history / ผลการรัน
2. **CONFIG ต้องเป็น prod ก่อนใช้งานจริง** — `env='prod'`, `testYm=''`, `reprocess=false`, `dryRun=false` (ค่าปัจจุบันถูกต้อง); การตั้ง `testYm` ใน env prod จะ throw error ป้องกันพลาด
3. **Folder ID ฝังใน CONFIG** — ถ้า folder ใน Drive ถูกลบ/สร้างใหม่ ต้องแก้ ID ใน `02_create_files_oag`
4. ค่า toner ใช้เฉพาะสีแรกในอีเมล (ปกติคือ Black)
5. จำกัด 500 อีเมลต่อรอบ (`maxResults`) — พอสำหรับ 37 เครื่อง/เดือน
6. ค่า `previousMonth = 0` ใช้ทั้งกรณี "ไม่มีไฟล์เดือนก่อน" และ "เครื่องใหม่" — ต่างกันที่เครื่องใหม่จะถูกไฮไลท์แดง
7. Credential ที่ใช้: Gmail OAuth2, Google Drive, Google Sheets OAuth2 (ผูกกับบัญชีเจ้าของ n8n)
8. ข้อมูลจริงยังน้อย (เพิ่งเริ่ม 10 ต.ค. 2026) — logic ผ่านการทดสอบด้วยอีเมลทดสอบเป็นหลัก ควรตรวจกับอีเมลจริงรอบแรก ๆ

---

## 9. แนวทางย้ายจาก n8n → Claude

### 9.1 การจับคู่ส่วนประกอบ

| ใน n8n | ใน Claude | เหตุผล |
|---|---|---|
| `Daily Sweep` (cron ทุกชั่วโมง) | **Scheduled task** (ทุกชั่วโมง `0 * * * *` — ขั้นต่ำของระบบคือรายชั่วโมง พอดีกับของเดิม) | ตัวกระตุ้นตามเวลา |
| `Gmail Trigger` (ทุก 1 นาที) | **ตัดทิ้ง** — ให้ sweep รายชั่วโมงทำหน้าที่แทน | Claude ไม่มี push จากอีเมล; sweep เดิมเก็บตกครบอยู่แล้ว ความหน่วงเพิ่มสูงสุด ~1 ชม. |
| `Manual Trigger` | **Skill** `counter-sync` สั่งรันเองพร้อม `--dry-run` | ใช้ทดสอบ/ตรวจสอบ |
| `Code` nodes (`Parse + Compute`, `Build Highlight`, `Compute Missing`, `Plan Labels` ฯลฯ) | **สคริปต์ Python** + unit test | logic ตายตัว ไม่ควรให้ LLM คำนวณทุกรอบ |
| `Gmail` nodes | Gmail connector (`search_threads`, `get_message`, `label_message`, `create_label`) หรือ Gmail API ในสคริปต์ | ระดับข้อความ (message id) เหมือนเดิม |
| `Google Drive` / `Google Sheets` nodes (รวม move file, highlight, `missing`) | connector ของ Drive/Sheets หรือ Google API (service account) ในสคริปต์ — **หรือ** ใช้ไฟล์ `.xlsx` ในโฟลเดอร์นี้เป็นแหล่งข้อมูลหลัก (ไฮไลท์ทำด้วย openpyxl fill) | ต้องตัดสินใจว่า "แหล่งจริง" คืออะไร (ดู 9.3) |
| `02_create_files_oag` | Skill/ฟังก์ชัน `ensure-monthly-files` (สถานะ `ok / misplaced / missing`) ที่ `counter-sync` เรียกก่อนทุกครั้ง | คงพฤติกรรม idempotent ถ้าย้ายมาใช้ไฟล์ในเครื่อง ขั้น "move" จะกลายเป็นแค่การวางไฟล์ใน `02_historys` / `03_report_files` |
| `Alert (choose channel)` | แจ้งเตือนจริง (push / ร่างอีเมล) เมื่อมี `ERROR_*` หรือแถวติดธงแดง | ของเดิมยังไม่ทำงาน — โอกาสปรับปรุง |
| `Build Names` / `Build Specs` CONFIG | ไฟล์ config (เช่น `config.yaml`) ข้างสคริปต์ มีคีย์ `env`, `dry_run`, `reprocess`, `sender`, master, flag color | จุดแก้ไขเดียวเหมือนเดิม |
| History sheet | คงไว้ (ใช้เป็น idempotency key) | หัวใจกันประมวลผลซ้ำ |

### 9.2 Hooks — ใช้เป็น guardrail ไม่ใช่ trigger

Hooks ของ Claude ทำงานเมื่อเกิดเหตุการณ์ **ภายใน session** (ก่อน/หลังเรียกเครื่องมือ, เริ่ม session, ส่ง prompt, หยุดตอบ) **ไม่ใช่เมื่ออีเมลเข้า หรือเมื่อถึงเวลา** จึงใช้แทน Gmail Trigger/cron ไม่ได้ ที่เหมาะคือ:
- `PreToolUse`: บล็อกการเขียนตรงเข้า `02_historys/` และ `03_report_files/` ถ้าไม่ได้ผ่านสคริปต์ที่กำหนด; บล็อกการตั้ง config เป็นโหมดทดสอบ (`env=test`, `testYm`) ใน prod
- `PostToolUse`: ตรวจหัวคอลัมน์/จำนวนคอลัมน์หลังเขียนไฟล์ (9 คอลัมน์ report, 5 คอลัมน์ history)
- `SessionStart`: สรุปสถานะเดือนนี้ (ส่งแล้ว/ยังไม่ส่ง, แถวติดธงแดง, error ค้าง)

### 9.3 ข้อควรตัดสินใจก่อนถอด n8n

1. **แหล่งข้อมูลจริงอยู่ที่ไหน** — ถ้ามีคนอื่นเปิดดู Google Sheets อยู่ ต้องให้ Claude เขียนกลับ Sheets (ไม่ใช่แค่ xlsx ในเครื่อง) ไม่เช่นนั้นสองที่จะไม่ตรงกัน
2. **ต้นทุน** — scheduled task แต่ละรอบเป็น session ใหม่ที่เรียก LLM; ให้สคริปต์เช็ค "มีอีเมลใหม่ไหม" ก่อน (fast path) ถ้าไม่มีให้จบทันที แต่ยังต้องอัปเดตชีต `missing` เมื่อมีการเปลี่ยนแปลง
3. **Session ใหม่ทุกรอบไม่มีความจำ** — prompt ของ scheduled task ต้องบอกครบ (path สคริปต์, config, โหมด dry-run/จริง)
4. **การอนุมัติ** — รันไม่มีคนเฝ้า การเขียนข้อมูลต้องตั้งสิทธิ์ให้ทำงานได้โดยไม่ต้องรออนุมัติ
5. **Sweep รายชั่วโมงเดียวพอ** — ความหน่วงสูงสุด ~1 ชม.
6. คงพฤติกรรม **dry-run** และโหมด **test ที่แยก prefix (`zz-test-oag`)** ไว้ เพราะช่วยทดสอบได้ปลอดภัย
7. **การไฮไลท์แถวแดง** — ถ้าใช้ Google Sheets ต้องเรียก `batchUpdate`; ถ้าใช้ xlsx ใช้ fill สีเดียวกัน (`FF6666`)

### 9.4 โครงที่แนะนำ

```
.claude/skills/counter-sync/SKILL.md     # วิธีรัน, dry-run, ตรวจผล, แก้ error
scripts/counter/
  config.yaml                            # env, sender, master id, folder ids, flag color
  ensure_files.py                        # ok / misplaced / missing → create / move / label
  parse_email.py                         # regex ตามหัวข้อ 3
  compute.py                             # กติกาหัวข้อ 7 (สถานะ, diff, superseded, flag)
  missing.py                             # คำนวณ sheet missing
  run.py --dry-run | --reprocess | --env test
tests/                                   # อีเมลตัวอย่าง + ผลที่คาดหวังของทุกสถานะ
```

ควรทำสคริปต์ให้ใช้ร่วมกันได้ทั้งชุด mwd และ oag (ต่างกันที่ config: prefix, sender, master, และเปิด/ปิด flag highlight + กติกา `previousMonth` กรณีไม่มีไฟล์เดือนก่อน)

### 9.5 Checklist ก่อนปิด n8n

- [ ] รัน dry-run ของระบบใหม่เทียบกับผลของ n8n ในเดือนเดียวกัน (ผลต้องตรงทุกแถว)
- [ ] ทดสอบทุกสถานะ: `COMPLETE`, `SUPERSEDED`, `SKIPPED_OTHER_MONTH`, `ERROR_*`
- [ ] ทดสอบกรณีไม่มีไฟล์เดือนก่อน / เครื่องไม่มีในเดือนก่อน (ต้องไฮไลท์แดง) / ไม่มีอีเมลใหม่
- [ ] ทดสอบกรณีไฮไลท์ล้มเหลว และเขียน `missing` ล้มเหลว (ที่ n8n ยังไม่เคยทดสอบ)
- [ ] ทดสอบรอยต่อขึ้นเดือนใหม่ (สร้างไฟล์ + ย้ายเข้า folder + สร้าง label อัตโนมัติ)
- [ ] ตั้ง Alert จริงสำหรับ `ERROR_*` และเครื่องติดธง
- [ ] ปิด (ไม่ลบ) workflow n8n ทั้ง 2 ตัวไว้ก่อนช่วงทดลองคู่ขนาน แล้วค่อยลบ
- [ ] ป้องกันสองระบบเขียนทับกัน — ห้ามเปิดทั้ง n8n และระบบใหม่พร้อมกันในโหมดเขียนจริง
