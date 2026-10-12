# 02_สตง — รายงานตัวนับเครื่องถ่ายเอกสาร สตง. (oag)

ใช้ Claude Cowork อ่านอีเมลตัวนับของเดือนที่ระบุ แล้วสร้างไฟล์รายงาน `.xlsx` ที่นี่ (ไม่มี n8n)

## วิธีใช้
```
/nnp-counter-oag 2026-09          ← ทำเฉพาะ สตง. เดือน ก.ย. 2026
/nnp-counter-all 2026-09          ← ทำ สตง. + ประปา พร้อมกัน
/nnp-counter-oag 2026-09 --dry-run ← ซ้อม ไม่แตะไฟล์จริง ไม่ติด label
```
ไม่ใส่เดือน → ระบบถามกลับ · ครั้งแรกบนเครื่องใหม่ให้พิมพ์ `/init-nnp-counter-skills`

## โครงสร้างโฟลเดอร์
| โฟลเดอร์ | เนื้อหา | ชื่อไฟล์ |
|----------|---------|----------|
| `01_master/` | รายชื่อเครื่อง 37 เครื่อง (unit, machine, building) — **ผู้ใช้ดูแลเอง** | `master_oag.xlsx` |
| `02_historys/` | ประวัติอีเมลที่ประมวลแล้ว (Id, ThreadId, SerialNumber, Status, Timestamp) | `oag-flow-history-YYYY-MM.xlsx` |
| `03_report_files/` | รายงานรายเดือน | `oag-YYYY-MM.xlsx` |

## ไฟล์รายงาน `oag-YYYY-MM.xlsx`
- **Sheet1**: machineDate, serialNumber, machineModel, unit, building, previousMonth, totalCounter, diff, remaining (% toner ดำเป็นเศษส่วน)
- **missing**: เครื่องใน master ที่ยังไม่ส่งรายงานเดือนนั้น + สรุป ทั้งหมด/ส่งแล้ว/ยังไม่ส่ง/อัปเดตล่าสุด
- แถว **สีแดง** = เครื่องที่ไม่มีในรายงานเดือนก่อน (ตรวจว่าเครื่องใหม่หรือข้อมูลเดือนก่อนตกหล่น)
- ไม่มีรายงานเดือนก่อนเลย → previousMonth = 0, diff = totalCounter (ไม่ระบายแดง)

## ผู้ส่งและ label
อีเมลจาก `networkservice@oag.go.th` · ติด label Gmail `oag-YYYY-MM` ให้ข้อความที่ประมวลแล้ว

## หากพบปัญหา
- diff ติดลบ → มิเตอร์รีเซ็ต/เครื่องเปลี่ยน — ตรวจเอง (ระบบเตือนแต่ไม่แก้)
- สถานะ `ERROR_*` ใน history → แก้ที่ต้นเหตุ (master ไม่มี serial ฯลฯ) แล้วสั่งเดือนเดิมซ้ำ จะลองใหม่เฉพาะที่ error
- สั่งเดือนเดิมซ้ำได้ปลอดภัย (ไม่ซ้ำแถว ไม่ซ้ำ label)
กติกาละเอียด: `CLAUDE.md`, `agents/oag/AGENT.md`
