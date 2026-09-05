"""
[metadata]
script_name = etl.py
description = [模組名稱] 開放資料清洗與入庫 ETL 腳本
category = etl
version = 1.0.0
"""

import json
import sqlite3
import csv
from pathlib import Path
from typing import Union, Dict, Any, List
from datetime import datetime

def parse_taiwan_date(date_str: str) -> str:
    """將民國年月日 (如 115/08/20 或 115.08.20) 轉換為 ISO 8601 (2026-08-20)"""
    if not date_str:
        return ""
    try:
        clean = date_str.strip().replace("-", "/").replace(".", "/")
        parts = clean.split("/")
        if len(parts) == 3:
            year = int(parts[0]) + 1911
            month = int(parts[1])
            day = int(parts[2])
            return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        pass
    return date_str

def run_etl(source_file: Union[str, Path], db_path: Union[str, Path]) -> Dict[str, Any]:
    src_p = Path(source_file)
    db_p = Path(db_path)
    if not src_p.exists():
        raise FileNotFoundError(f"來源資料檔不存在: {src_p}")
    
    db_p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_p))
    cursor = conn.cursor()
    
    # 執行模組 schema
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    # TODO: 實作特定業務之資料清洗與插入邏輯
    
    conn.commit()
    conn.close()
    return {"status": "SUCCESS", "source": str(src_p), "processed_at": datetime.now().isoformat()}

if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "data/samples/sample.json"
    db = sys.argv[2] if len(sys.argv) > 2 else "db/fsc.db"
    res = run_etl(src, db)
    print(json.dumps(res, ensure_ascii=False, indent=2))
