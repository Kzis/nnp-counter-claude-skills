# 01_ประปา — รายงานตัวนับเครื่องถ่ายเอกสาร การประปา (mwd)

ใช้ Claude Cowork อ่านอีเมลตัวนับของเดือนที่ระบุ แล้วสร้างไฟล์รายงาน `.xlsx` ที่นี่ (ไม่มี n8n)

## วิธีใช้
```
/nnp-counter-mwd 2026-09          ← ทำเฉพาะ ประปา เดือน ก.ย. 2026
/nnp-counter-all 2026-09          ← ทำ สตง. + ประปา พร้อมกัน
/nnp-counter-mwd 2026-09 --dry-run ← ซ้อม ไม่แตะไฟล์จริง ไม่ติด label
```
ไม่ใส่เดือน → ระบบถามกลับ · ครั้งแรกบนเครื่องใหม่ให้พิมพ์ `/init-nnp-counter-skills`

## โครงสร้างโฟลเดอร์
| โฟลเดอร์ | เนื้อหา | ชื่อไฟล์ |
|----------|---------|----------|
| `01_master/` | รายชื่อเครื่อง 119 เครื่อง (แท็บ `master`: unit, building, machine, start, current, count) — **ผู้ใช้ดูแลเอง** | `master_mwd.xlsx` |
| `02_historys/` | ประวัติอีเมลที่ประมวลแล้ว (Id, ThreadId, SerialNumber, Status, Timestamp) | `mwd-flow-history-YYYY-MM.xlsx` |
| `03_report_files/` | รายงานรายเดือน | `mwd-YYYY-MM.xlsx` |

## ไฟล์รายงาน `mwd-YYYY-MM.xlsx`
- **Sheet1**: machineDate, serialNumber, machineModel, unit, building, previousMonth, totalCounter, diff, remaining (% toner ดำเป็นเศษส่วน)
- **missing**: เครื่องใน master ที่ยังไม่ส่งรายงานเดือนนั้น + สรุป ทั้งหมด/ส่งแล้ว/ยังไม่ส่ง/อัปเดตล่าสุด
- ไม่มีรายงานเดือนก่อน → previousMonth/diff เว้นว่าง · เครื่องที่ไม่มีในเดือนก่อน → previousMonth 0 (ไม่ระบายสี)

## ผู้ส่งและ label
อีเมลจาก `pachara.l@mwa.co.th` (~250 ข้อความ/เดือน หลายข้อความต่อเครื่อง — ใช้ฉบับที่ **วันที่ของเครื่องล่าสุด**) · ติด label Gmail `mwd-YYYY-MM`

## หากพบปัญหา
- diff ติดลบ → มิเตอร์รีเซ็ต/เครื่องเปลี่ยน — ตรวจเอง (ระบบเตือนแต่ไม่แก้)
- สถานะ `ERROR_*` ใน history → แก้ที่ต้นเหตุแล้วสั่งเดือนเดิมซ้ำ จะลองใหม่เฉพาะที่ error
- สั่งเดือนเดิมซ้ำได้ปลอดภัย (ไม่ซ้ำแถว ไม่ซ้ำ label)
กติกาละเอียด: `CLAUDE.md`, `agents/mwd/AGENT.md`
