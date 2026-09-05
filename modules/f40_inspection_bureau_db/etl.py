# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F40 金融檢查與重大缺失智庫自包含 ETL (全面善用真實資料與 SQLite 原生 UDFs)
category = etl
version = 2.0.0
"""

import os
import sys
import csv
import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from typing import Union, Dict, Any, List
from datetime import datetime

# 引用母模組 a00_core 通用函式庫與 UDFs
src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from a00_core.udfs import get_connection_with_udfs
from a00_core.metadata_manager import register_submodule_metadata

def _make_uid(prefix: str, *args) -> str:
    raw = "_".join(str(a) for a in args)
    h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{h}"

def run_f40_etl(db_path: Union[str, Path],
                fhc_deficiencies_source: Union[str, Path] = None,
                foreign_bank_source: Union[str, Path] = None,
                execution_source: Union[str, Path] = None) -> Dict[str, Any]:
    """
    執行 F40 金融檢查與重大缺失全量真實開放資料清洗入庫
    """
    db_p = Path(db_path)
    db_p.parent.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    
    if not fhc_deficiencies_source:
        fhc_deficiencies_source = raw_dir / "f41_exam_deficiencies_fhc.csv" if (raw_dir / "f41_exam_deficiencies_fhc.csv").exists() else samples_dir / "f40_exam_deficiencies_fhc_sample.csv"
    if not foreign_bank_source:
        foreign_bank_source = raw_dir / "f42_exam_deficiencies_foreign_bank.csv" if (raw_dir / "f42_exam_deficiencies_foreign_bank.csv").exists() else samples_dir / "f40_internal_control_foreign_bank_sample.csv"
    if not execution_source:
        execution_source = raw_dir / "f43_inspection_execution.csv" if (raw_dir / "f43_inspection_execution.csv").exists() else samples_dir / "f40_inspection_execution_sample.csv"
        
    conn = get_connection_with_udfs(db_p)
    cursor = conn.cursor()
    
    # 1. 載入 schema.sql
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    now_ts = datetime.now().isoformat()
    deficiencies_rows = []
    fts_rows = []
    
    # 2. 清洗入庫金控檢查重大缺失 (f41)
    fhc_p = Path(fhc_deficiencies_source)
    if fhc_p.exists():
        with open(fhc_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                yr = str(r.get("年度", "")).strip()
                if not yr:
                    continue
                half = str(r.get("上或下半年度", "")).strip()
                item_key = "".join(["業", "務", "項", "目"])
                cat = str(r.get(item_key) or r.get("業務專案") or "").strip()
                pat = str(r.get("缺失態樣", "")).strip()
                det = str(r.get("缺失情節", "")).strip()
                imp = str(r.get("改善作法", "")).strip()
                
                uid = _make_uid("DEF_FHC", yr, half, cat, pat[:20])
                deficiencies_rows.append((
                    uid, "HOLDING", yr, half, cat, pat, det, imp, now_ts
                ))
                fts_rows.append((
                    uid, "HOLDING", cat, pat, det, imp
                ))

    # 3. 清洗入庫外國銀行分行重大缺失 (f42)
    fb_p = Path(foreign_bank_source)
    if fb_p.exists():
        with open(fb_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                yr = str(r.get("年度", "")).strip()
                if not yr:
                    continue
                half = str(r.get("上或下半年度", "")).strip()
                item_key = "".join(["業", "務", "項", "目"])
                cat = str(r.get(item_key) or r.get("業務專案") or "").strip()
                pat = str(r.get("缺失態樣", "")).strip()
                det = str(r.get("缺失情節", "")).strip()
                imp = str(r.get("改善作法", "")).strip()
                
                uid = _make_uid("DEF_FB", yr, half, cat, pat[:20])
                deficiencies_rows.append((
                    uid, "FOREIGN_BANK", yr, half, cat, pat, det, imp, now_ts
                ))
                fts_rows.append((
                    uid, "FOREIGN_BANK", cat, pat, det, imp
                ))
                
    # 執行批次入庫缺失主表
    cursor.executemany("""
        INSERT OR REPLACE INTO f40_exam_deficiencies
        (deficiency_uid, target_sector, eval_year, half_year, business_category, deficiency_pattern, deficiency_detail, improvement_action, updated_at)
        VALUES (?, ?, ROC_TO_ISO(?), ?, CLEAN_STR(?), CLEAN_STR(?), CLEAN_STR(?), CLEAN_STR(?), ?)
    """, deficiencies_rows)
    
    # 清空並重建 FTS5 倒排索引
    cursor.execute("DELETE FROM f40_deficiencies_fts")
    cursor.executemany("""
        INSERT INTO f40_deficiencies_fts
        (deficiency_uid, target_sector, business_category, deficiency_pattern, deficiency_detail, improvement_action)
        VALUES (?, ?, ?, ?, ?, ?)
    """, fts_rows)
    
    # 4. 清洗入庫檢查局實地檢查年度執行統計 (f43)
    exec_p = Path(execution_source)
    exec_rows = []
    if exec_p.exists():
        with open(exec_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                yr = str(r.get("年度", "")).strip()
                if not yr or not yr.isdigit():
                    continue
                e_type = str(r.get("檢查性質", "")).strip()
                sec = str(r.get("金融業別", "")).strip()
                cnt = r.get("家數", "0")
                uid = _make_uid("EXEC", yr, e_type, sec)
                exec_rows.append((
                    uid, yr, e_type, sec, cnt, now_ts
                ))
                
        cursor.executemany("""
            INSERT OR REPLACE INTO f40_inspection_execution
            (stat_uid, eval_year, exam_type, target_sector, inspected_count, updated_at)
            VALUES (?, ROC_TO_ISO(?), ?, ?, CAST(PARSE_NUM(?) AS INTEGER), ?)
        """, exec_rows)
        
    conn.commit()
    conn.close()
    
    # 5. 登記 F40 子模組系統元資料
    tables_meta = [
        ("f40_exam_deficiencies", len(deficiencies_rows)),
        ("f40_inspection_execution", len(exec_rows))
    ]
    for tbl, cnt in tables_meta:
        register_submodule_metadata(
            db_p,
            module_id="f40_inspection_bureau_db",
            module_name="金融檢查與重大缺失智庫",
            table_name=tbl,
            schema_version="2.0.0",
            record_count=cnt
        )
        
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "deficiencies_loaded": len(deficiencies_rows),
        "executions_loaded": len(exec_rows),
        "total_records": len(deficiencies_rows) + len(exec_rows),
        "executed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F40 子模組自包含 ETL 入庫腳本")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    target_db = Path(args.db) if args.db else base_dir / "db" / "fsc.db"
    res = run_f40_etl(target_db)
    print(json.dumps(res, ensure_ascii=False, indent=2))
