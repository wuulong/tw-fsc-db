# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F30 保險市場與精算風險智庫自包含 ETL (全面善用真實資料與 SQLite 原生 UDFs)
category = etl
version = 2.0.0
"""

import os
import sys
import csv
import json
import sqlite3
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

def run_f30_etl(db_path: Union[str, Path],
                hr_source: Union[str, Path] = None,
                complaints_source: Union[str, Path] = None,
                fund_source: Union[str, Path] = None) -> Dict[str, Any]:
    """
    執行 F30 保險市場與精算風險全量真實開放資料清洗入庫
    """
    db_p = Path(db_path)
    db_p.parent.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    
    if not hr_source:
        hr_source = raw_dir / "f31_insurance_hr.json" if (raw_dir / "f31_insurance_hr.json").exists() else samples_dir / "f30_insurance_hr_sample.json"
    if not complaints_source:
        complaints_source = raw_dir / "f32_insurance_complaints.csv" if (raw_dir / "f32_insurance_complaints.csv").exists() else samples_dir / "f30_insurance_complaints_sample.csv"
    if not fund_source:
        fund_source = raw_dir / "f33_special_compensation_fund.csv" if (raw_dir / "f33_special_compensation_fund.csv").exists() else samples_dir / "f30_special_compensation_fund_sample.csv"
        
    conn = get_connection_with_udfs(db_p)
    cursor = conn.cursor()
    
    # 1. 載入 schema.sql
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    now_ts = datetime.now().isoformat()
    
    # 2. 清洗入庫保險機構人力與精算人員 f30_insurance_institutions
    hr_p = Path(hr_source)
    insurers_count = 0
    if hr_p.exists():
        hr_data = json.loads(hr_p.read_text(encoding="utf-8-sig"))
        raw_hr_rows = []
        for d in hr_data:
            name = d.get("INSURER_Name", "").strip()
            if not name:
                continue
            i_type = "LIFE" if "人壽" in name else ("PROPERTY" if "產物" in name else "COOP")
            raw_hr_rows.append((
                name,
                i_type,
                d.get("Cnt2", "0"),
                d.get("Cnt3", "0"),
                d.get("Underwriting", "0"),
                d.get("Claim", "0"),
                d.get("Actuary", "0"),
                d.get("OccurDate", "2026-06-30"),
                now_ts
            ))
            
        cursor.executemany("""
            INSERT OR REPLACE INTO f30_insurance_institutions
            (insurer_name, insurer_type, inner_staff_count, field_agent_count, underwriting_count, claim_count, actuary_count, report_date, updated_at)
            VALUES (
                CLEAN_STR(?),
                ?,
                CAST(PARSE_NUM(?) AS INTEGER),
                CAST(PARSE_NUM(?) AS INTEGER),
                CAST(PARSE_NUM(?) AS INTEGER),
                CAST(PARSE_NUM(?) AS INTEGER),
                CAST(PARSE_NUM(?) AS INTEGER),
                ROC_TO_ISO(?),
                ?
            )
        """, raw_hr_rows)
        insurers_count = len(raw_hr_rows)
        
    # 3. 清洗入庫保險爭議申訴趨勢 f30_insurance_complaint_trends
    comp_p = Path(complaints_source)
    complaints_count = 0
    if comp_p.exists():
        with open(comp_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            raw_comp_rows = []
            for r in reader:
                yr = str(r.get("年", "")).strip()
                if not yr or not yr.isdigit():
                    continue
                raw_comp_rows.append((
                    yr,
                    r.get("簽單契約件數_千", "0"),
                    r.get("申訴件數", "0"),
                    r.get("申訴比率", "0"),
                    r.get("和解件數", "0"),
                    r.get("和解占申訴案件比率%", "0"),
                    r.get("依申訴人意見辦理占申訴案件比率%", "0"),
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f30_insurance_complaint_trends
                (eval_year, policy_contract_thousand, complaint_count, complaint_ratio, settlement_count, settlement_ratio, complainant_favored_ratio, updated_at)
                VALUES (
                    ?,
                    PARSE_NUM(?),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    PARSE_NUM(?),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    ?
                )
            """, raw_comp_rows)
            complaints_count = len(raw_comp_rows)
            
    # 4. 清洗入庫特別補償基金運作表 f30_special_compensation_fund
    fund_p = Path(fund_source)
    fund_count = 0
    if fund_p.exists():
        with open(fund_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            raw_fund_rows = []
            for r in reader:
                yr = str(r.get("年", "")).strip()
                if not yr or not yr.isdigit():
                    continue
                exp = r.get("補償支出", "0")
                cases = r.get("補償件數", "0")
                raw_fund_rows.append((
                    yr,
                    r.get("分擔額收入", "0"),
                    exp,
                    cases,
                    exp,
                    cases,
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f30_special_compensation_fund
                (stat_year, contribution_income_thousand, compensation_expense_thousand, compensated_cases, avg_compensation_thousand, updated_at)
                VALUES (
                    ?,
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    ROUND(PARSE_NUM(?) / MAX(CAST(PARSE_NUM(?) AS INTEGER), 1), 2),
                    ?
                )
            """, raw_fund_rows)
            fund_count = len(raw_fund_rows)
            
    conn.commit()
    conn.close()
    
    # 5. 登記 F30 子模組元資料 (sys_module_metadata)
    tables_meta = [
        ("f30_insurance_institutions", insurers_count),
        ("f30_insurance_complaint_trends", complaints_count),
        ("f30_special_compensation_fund", fund_count)
    ]
    for tbl, cnt in tables_meta:
        register_submodule_metadata(
            db_p,
            module_id="f30_insurance_actuarial_db",
            module_name="保險市場與精算風險資料庫",
            table_name=tbl,
            schema_version="2.0.0",
            record_count=cnt
        )
        
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "insurers_loaded": insurers_count,
        "complaints_loaded": complaints_count,
        "fund_loaded": fund_count,
        "total_records": insurers_count + complaints_count + fund_count,
        "executed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F30 子模組自包含 ETL 入庫腳本")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    parser.add_argument("--hr-source", default=None, help="保險人力資料路徑")
    parser.add_argument("--complaints-source", default=None, help="保險申訴資料路徑")
    parser.add_argument("--fund-source", default=None, help="特別補償基金資料路徑")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    if not args.db:
        target_db = base_dir / "db" / "fsc.db"
    else:
        target_db = Path(args.db)
        
    res = run_f30_etl(target_db, hr_source=args.hr_source, complaints_source=args.complaints_source, fund_source=args.fund_source)
    print(json.dumps(res, ensure_ascii=False, indent=2))
