# nnp-counter

ระบบอ่านอีเมลตัวนับเครื่องถ่ายเอกสารจาก Gmail → สร้างรายงาน `.xlsx` รายเดือน ของ **สตง. (oag)** และ **ประปา (mwd)** ทำงานในเครื่องผ่าน Claude Cowork

เริ่มต้น: เปิดโฟลเดอร์นี้ใน Claude Cowork แล้วพิมพ์ `/init-nnp-counter-skills` → จากนั้น `/nnp-counter-all YYYY-MM` (ลอง `--dry-run` ก่อนได้)

| ต้องการ | อ่าน |
|---------|------|
| วิธีทำงาน / กฎ / flow | `CLAUDE.md` |
| คู่มือแต่ละองค์กร | `01_ประปา/README.md`, `02_สตง/README.md` |
| คำสั่งของ agent | `agents/{oag,mwd}/AGENT.md` |
| ตัวช่วยย่อย | `skills/nnp-*/SKILL.md` |
| ผลทดสอบความเป็นไปได้ | `docs/phase0-findings.md` |
| สเปก n8n เดิม (อ้างอิง) | `docs/n8n-legacy.md` |

ทดสอบ: `pip install -r requirements-dev.txt && python3 -m pytest -q tests`
