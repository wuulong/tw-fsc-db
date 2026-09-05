# -*- coding: utf-8 -*-
"""
[metadata]
spec = "AXX_SPECIFICATION.md"
manual = "CLI_MANUAL.md"
"""

import sys
import json
import sqlite3
from pathlib import Path

def init_submodule_db(db_path: Path):
    """初始化子模組 Table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xx_submodule_data (
            uid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
