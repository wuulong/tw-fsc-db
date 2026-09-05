# -*- coding: utf-8 -*-
"""
[metadata]
name = metadata_manager.py
description = 全域子模組元資料與資料表統計登錄管理器
category = core
version = 1.0.0
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

def register_submodule_metadata(
    db_path: Path,
    module_id: str,
    module_name: str,
    table_name: str,
    schema_version: str = "1.0.0",
    record_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    將子模組的運作狀態與資料表筆數登錄至 sys_module_metadata 系統表
    """
    db_p = Path(db_path)
    conn = sqlite3.connect(str(db_p))
    cursor = conn.cursor()
    
    # 確保系統表存在
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sys_module_metadata (
            module_id TEXT NOT NULL,
            module_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_count INTEGER DEFAULT 0,
            schema_version TEXT DEFAULT '1.0.0',
            last_updated TEXT NOT NULL,
            PRIMARY KEY (module_id, table_name)
        )
    """)
    
    # 若未提供 record_count，動態查詢
    if record_count is None:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            cnt_row = cursor.fetchone()
            record_count = cnt_row[0] if cnt_row else 0
        except Exception:
            record_count = 0
            
    now_ts = datetime.now().isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO sys_module_metadata
        (module_id, module_name, table_name, record_count, schema_version, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (module_id, module_name, table_name, record_count, schema_version, now_ts))
    
    conn.commit()
    conn.close()
    
    return {
        "module_id": module_id,
        "table_name": table_name,
        "record_count": record_count,
        "last_updated": now_ts
    }

def get_all_registered_modules(db_path: Path) -> List[Dict[str, Any]]:
    """取得所有已註冊子模組之健康狀態與資料統計"""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT module_id, module_name, table_name, record_count, schema_version, last_updated
            FROM sys_module_metadata
            ORDER BY module_id, table_name
        """)
        rows = [dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    return rows
