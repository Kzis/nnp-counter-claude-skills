from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENTRY = ["init-nnp-counter-skills", "nnp-counter-oag", "nnp-counter-mwd", "nnp-counter-all"]


def test_entry_skill_copies_in_sync():
    for s in ENTRY:
        a = (REPO / "skills" / s / "SKILL.md").read_text(encoding="utf-8")
        b = (REPO / ".claude" / "skills" / s / "SKILL.md").read_text(encoding="utf-8")
        assert a == b, s


def test_every_skill_has_frontmatter_and_name_matches():
    for d in (REPO / "skills").iterdir():
        t = (d / "SKILL.md").read_text(encoding="utf-8")
        assert t.startswith("---\nname: " + d.name + "\ndescription: "), d.name


def test_agent_docs_reference_existing_skills():
    import re
    names = {d.name for d in (REPO / "skills").iterdir()}
    for org in ("oag", "mwd"):
        t = (REPO / "agents" / org / "AGENT.md").read_text(encoding="utf-8")
        for n in re.findall(r"nnp-[a-z-]+", t):
            assert n in names, (org, n)
