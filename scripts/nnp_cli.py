#!/usr/bin/env python3
"""จุดเข้าเดียวของระบบ: python3 scripts/nnp_cli.py <command> --org <oag|mwd> --month YYYY-MM"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nnp_counter.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
