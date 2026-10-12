---
name: nnp-gmail-connect
description: เชื่อมและค้น Gmail อย่างถูกต้อง: โหลดเครื่องมือ, ค้นด้วย query บังคับ, อ่าน thread ใหญ่, ส่งข้อมูลเข้า add-meta ใช้ทุกครั้งที่ดึงอีเมล
---

# เชื่อม Gmail และดึงอีเมล

## 1. ตรวจการเชื่อมต่อ
ToolSearch (เครื่องมือ Gmail อาจเป็น deferred ต้องโหลดก่อนเรียกทุกตัว) `select:mcp__Gmail__search_threads,mcp__Gmail__get_thread,mcp__Gmail__get_message,mcp__Gmail__list_labels,mcp__Gmail__create_label,mcp__Gmail__label_message`
แล้วเรียก `list_labels` — ได้รายการ = เชื่อมแล้ว. ถ้าไม่มีเครื่องมือ/ error ให้หยุดและรายงาน "ยังไม่ได้เชื่อม Gmail connector" (ผู้ใช้เชื่อมใน Settings → Connectors → Gmail)

## 2. ค้น (ใช้ `gmail_query` จาก `begin` ตามตัวอักษร)
`search_threads(query=gmail_query, pageSize=50)` วนด้วย `pageToken` จนหมด
> ⚠ ผลค้นเป็นระดับ **thread** และ preview แสดงแค่ ~5 ข้อความเก่าสุดของ thread — 1 thread อาจมีได้ถึง ~100 ข้อความ ห้ามถือว่า 1 อีเมล = 1 thread

ทุก thread ที่ `messageCount > 5` (หรือเพื่อความปลอดภัย: ทุก thread ที่ messageCount > จำนวนที่เห็น) ให้ `get_thread` (MINIMAL) เพื่อได้ข้อความครบ
ผลใหญ่จะถูกบันทึกเป็นไฟล์ → ประมวลด้วย jq/python ที่ไฟล์นั้น แทนการคัดลอกด้วยมือ

## 3. สร้าง JSONL เข้า `add-meta`
หนึ่งบรรทัดต่อข้อความ (เฉพาะข้อความที่ `sender` = ผู้ส่งขององค์กรนั้น; ฉบับร่าง draft ข้าม):
```json
{"id":"<messageId>","threadId":"<threadId>","internalDate":"<epoch ms>","sender":"<อีเมลผู้ส่ง>","text":"<snippet>"}
```
ส่งผ่าน stdin ครั้งละ ≤ ~50 บรรทัด (หรือเขียนไฟล์ใน `_work/inbox/` แล้ว `< ไฟล์`):
`python3 scripts/nnp_cli.py add-meta --org <org> --month <M> < batch.jsonl`
ผลลัพธ์: accepted / duplicates / already_done / rejected_wrong_sender / rejected_invalid — **ต้องตรวจว่า rejected_invalid ว่าง** และ accepted+duplicates = จำนวนที่ส่ง
ห้ามแก้เนื้อ snippet (คัดลอกตรงตัว) — ตัวเลขผิดตัวเดียว = รายงานผิด; `audit` จะสุ่มเทียบกลับกับ Gmail

## 3.1 เส้นทางไฟล์ (thread ใหญ่/จำนวนมาก)
`get_thread` ที่ใหญ่จะถูกเก็บเป็นไฟล์ในคอนเทนเนอร์คลาวด์ (คนละเครื่องกับโฟลเดอร์งานของผู้ใช้) ให้:
1. แปลงด้วย jq/python ในคอนเทนเนอร์เป็น JSONL ตามรูปแบบข้างบน (ข้ามข้อความที่ sender ไม่ตรง; จำนวนที่ได้อาจน้อยกว่า `messageCount` เล็กน้อย เพราะร่าง draft ไม่ถูกส่งมา — ปกติ)
2. เขียนไฟล์ใต้ `/mnt/user-data/outputs/` แล้ว `device_commit_files` ไปที่ `<path โฟลเดอร์งานบนเครื่องผู้ใช้>/_work/inbox/<ชื่อ>.jsonl` (path เต็มได้จาก `get_device_info` → connectedFolders; Windows ใช้ `C:\...\_work\inbox\x.jsonl` ได้)
3. `python3 scripts/nnp_cli.py add-meta --org <org> --month <M> < _work/inbox/<ชื่อ>.jsonl`
ห้ามให้ jq/สคริปต์แก้ค่าใดๆ นอกจากจัดรูปแบบ
ผลค้นรวม (`resultCountEstimate`) อาจเกินจำนวนข้อความจริงเล็กน้อย (นับร่าง) — ใช้ผลของ `add-meta` (`total_in_meta`) เป็นตัวตัดสิน

## 4. ข้อควรระวัง
- ใช้เฉพาะเครื่องมืออ่าน/ติด label · ห้าม send_message, reply, forward, trash, delete_* ใดๆ
- ถ้าผลค้นว่าง → ยังต้อง `plan`/`apply` ตามปกติ (จะได้เครื่องที่ยังไม่ส่งทั้งหมด) แต่รายงานว่า "ไม่พบอีเมล"
