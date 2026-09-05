# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F10 銀行與信用金融模組自包含 ETL (全面善用全量真實開放資料與 SQLite 原生 UDFs)
category = etl
version = 2.2.0
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

def run_f10_etl(db_path: Union[str, Path],
                fhc_source: Union[str, Path] = None,
                banking_source: Union[str, Path] = None,
                land_source: Union[str, Path] = None,
                credit_source: Union[str, Path] = None,
                corporate_source: Union[str, Path] = None) -> Dict[str, Any]:
    """
    執行 F10 銀行與信用金融全量五大真實地面開放資料集清洗與入庫
    預設優先讀取 data/raw 全量真實資料；若指定 sample 檔案則依指定處理
    全面採用 SQLite 原生 UDF (ROC_TO_ISO, PARSE_NUM, CLEAN_STR, COUNT_DELIMITED, BANK_72_2_RATIO)
    """
    db_p = Path(db_path)
    db_p.parent.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    
    # 依真實資料優先原則：若 raw 存在則預設採用 raw，否則 fallback 至 samples
    if not fhc_source:
        fhc_source = raw_dir / "f10_fhc_setup.csv" if (raw_dir / "f10_fhc_setup.csv").exists() else samples_dir / "f10_fhc_setup_sample.csv"
    if not banking_source:
        banking_source = raw_dir / "f10_banking12.csv" if (raw_dir / "f10_banking12.csv").exists() else samples_dir / "f10_banking12_sample.csv"
    if not land_source:
        land_source = raw_dir / "f12_land_collateral_loan.csv" if (raw_dir / "f12_land_collateral_loan.csv").exists() else samples_dir / "f10_land_loan_sample.csv"
    if not credit_source:
        credit_source = raw_dir / "f13_credit_card_stats.csv" if (raw_dir / "f13_credit_card_stats.csv").exists() else samples_dir / "f10_credit_card_sample.csv"
    if not corporate_source:
        corporate_source = raw_dir / "f14_corporate_loan.csv" if (raw_dir / "f14_corporate_loan.csv").exists() else samples_dir / "f10_corporate_loan_sample.csv"
        
    conn = get_connection_with_udfs(db_p)
    cursor = conn.cursor()
    
    # 1. 載入最新 schema.sql (5 表 + 2 檢視表)
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    now_ts = datetime.now().isoformat()
    
    # 2. 清洗入庫金控資料 (f10_financial_holdings)
    fhc_count = 0
    fhc_p = Path(fhc_source)
    if fhc_p.exists():
        with open(fhc_p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_rows = []
            for r in reader:
                name = r.get("金控公司名稱", "")
                if not name or not name.strip() or "單位" in name:
                    continue
                raw_rows.append((
                    name,
                    r.get("核准設立日期", ""),
                    r.get("開業", ""),
                    r.get("集團資產(單位10億元)", ""),
                    r.get("集團淨值(單位10億元)", ""),
                    r.get("子公司", ""),
                    now_ts
                ))
            
            cursor.executemany("""
                INSERT OR REPLACE INTO f10_financial_holdings
                (holding_name, approved_date, opening_date, group_assets_billion, group_net_worth_billion, subsidiaries_text, subsidiaries_count, updated_at)
                VALUES (
                    CLEAN_STR(?),
                    ROC_TO_ISO(?),
                    ROC_TO_ISO(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    CLEAN_STR(?),
                    COUNT_DELIMITED(CLEAN_STR(?), '、'),
                    ?
                )
            """, [(r[0], r[1], r[2], r[3], r[4], r[5], r[5], r[6]) for r in raw_rows])
            fhc_count = len(raw_rows)
                
    # 3. 清洗入庫銀行資產品質資料 (f10_bank_asset_quality) - 涵蓋全臺 38 家商業銀行
    banking_count = 0
    bk_p = Path(banking_source)
    if bk_p.exists():
        with open(bk_p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_bank_rows = []
            for r in reader:
                name = r.get("銀行別", "")
                if not name or not name.strip() or "單位" in name or "資料月份" in name:
                    continue
                raw_bank_rows.append((
                    name,
                    r.get("存款", ""),
                    r.get("稅前盈餘", ""),
                    r.get("放款總額", ""),
                    r.get("逾期放款總額", ""),
                    r.get("貼現及放款提列之備抵呆帳", ""),
                    r.get("淨值", ""),
                    r.get("逾放比率(%)", ""),
                    r.get("備抵呆帳/逾期放款(%)", ""),
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f10_bank_asset_quality
                (bank_name, deposit_amount, pretax_profit, loan_total, overdue_loan_total, allowance_bad_debt, net_worth, npl_ratio, coverage_ratio, updated_at)
                VALUES (
                    CLEAN_STR(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    ?
                )
            """, raw_bank_rows)
            banking_count = len(raw_bank_rows)

    # 4. 清洗入庫土地擔保放款餘額 (f10_land_collateral_loans) - 涵蓋全臺商業銀行與信合社
    land_count = 0
    land_p = Path(land_source)
    if land_p.exists():
        with open(land_p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_land_rows = []
            for r in reader:
                name = r.get("金融機構", "")
                if not name or not name.strip() or "單位" in name or "資料月份" in name:
                    continue
                land_bal = r.get("以土地為擔保品之放款餘額", "")
                tot_loan = r.get("放款總額（含催收款）", "")
                raw_land_rows.append((
                    name,
                    land_bal,
                    tot_loan,
                    land_bal,
                    tot_loan,
                    now_ts
                ))
            
            cursor.executemany("""
                INSERT OR REPLACE INTO f10_land_collateral_loans
                (bank_name, land_loan_balance, total_loan_including_call, land_loan_ratio, updated_at)
                VALUES (
                    CLEAN_STR(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    BANK_72_2_RATIO(?, ?),
                    ?
                )
            """, raw_land_rows)
            land_count = len(raw_land_rows)

    # 5. 清洗入庫信用卡業務資訊 (f10_credit_card_operations)
    credit_count = 0
    cc_p = Path(credit_source)
    if cc_p.exists():
        with open(cc_p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_cc_rows = []
            for r in reader:
                inst = r.get("機構名稱", "")
                if not inst or not inst.strip() or "單位" in inst:
                    continue
                eff = r.get("流通卡數", "0")
                act = r.get("有效卡數", "0")
                raw_cc_rows.append((
                    inst,
                    eff,
                    act,
                    r.get("當月發卡數", "0"),
                    r.get("當月停卡數", "0"),
                    r.get("當月簽帳金額[百萬元]", "0"),
                    r.get("循環信用餘額[百萬元]", "0"),
                    r.get("逾期三個月以上帳款[百萬元]", "0"),
                    r.get("逾期六個月以上帳款[百萬元]", "0"),
                    act,
                    eff,
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f10_credit_card_operations
                (institution_name, cards_effective, cards_active, cards_issued_month, cards_revoked_month, 
                 signing_amount_million, revolving_balance_million, delinquent_over_3m_million, delinquent_over_6m_million, active_card_ratio, updated_at)
                VALUES (
                    CLEAN_STR(?),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    BANK_72_2_RATIO(?, ?),
                    ?
                )
            """, raw_cc_rows)
            credit_count = len(raw_cc_rows)

    # 6. 清洗入庫全台企業總貸款趨勢 (f10_corporate_loan_trends) - 全量月度趨勢
    corporate_count = 0
    corp_p = Path(corporate_source)
    if corp_p.exists():
        with open(corp_p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_corp_rows = []
            for r in reader:
                yr = str(r.get("年", "")).strip()
                mo = str(r.get("月", "")).strip().zfill(2)
                if not yr or not mo or not yr.isdigit():
                    continue
                ym = f"{yr}-{mo}"
                tot_thousand = r.get("企業貸款總金額[仟元]", "0")
                raw_corp_rows.append((
                    ym,
                    r.get("企業貸款總家數", "0"),
                    tot_thousand,
                    r.get("企業貸款平均金額[仟元]", "0"),
                    tot_thousand,
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f10_corporate_loan_trends
                (year_month, loan_entity_count, loan_total_thousand, loan_avg_thousand, loan_total_billion, updated_at)
                VALUES (
                    ?,
                    CAST(PARSE_NUM(?) AS INTEGER),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    ROUND(PARSE_NUM(?) / 1000000.0, 4),
                    ?
                )
            """, raw_corp_rows)
            corporate_count = len(raw_corp_rows)
                
    conn.commit()
    conn.close()
    
    # 7. 登記子模組元資料 (sys_module_metadata)
    tables_meta = [
        ("f10_financial_holdings", fhc_count),
        ("f10_bank_asset_quality", banking_count),
        ("f10_land_collateral_loans", land_count),
        ("f10_credit_card_operations", credit_count),
        ("f10_corporate_loan_trends", corporate_count)
    ]
    for tbl, cnt in tables_meta:
        register_submodule_metadata(
            db_p,
            module_id="f10_banking_credit_db",
            module_name="銀行與信用金融資料庫",
            table_name=tbl,
            schema_version="2.2.0",
            record_count=cnt
        )
    
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "fhc_records_loaded": fhc_count,
        "banking_records_loaded": banking_count,
        "land_loan_records_loaded": land_count,
        "credit_card_records_loaded": credit_count,
        "corporate_loan_records_loaded": corporate_count,
        "total_records": fhc_count + banking_count + land_count + credit_count + corporate_count,
        "source_type": "RAW_GROUND_TRUTH" if "raw" in str(banking_source) else "SAMPLE",
        "executed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F10 子模組自包含 ETL 入庫腳本 (真實全量開放資料 + 原生 UDFs)")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    parser.add_argument("--fhc-source", default=None, help="金控名冊資料路徑")
    parser.add_argument("--banking-source", default=None, help="銀行營運資料路徑")
    parser.add_argument("--land-source", default=None, help="土地放款資料路徑")
    parser.add_argument("--credit-source", default=None, help="信用卡資料路徑")
    parser.add_argument("--corporate-source", default=None, help="企貸趨勢資料路徑")
    parser.add_argument("--sample", action="store_true", help="強制使用 samples 目錄資料 (供測試使用)")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    if not args.db:
        target_db = base_dir / "db" / "fsc.db"
    else:
        target_db = Path(args.db)
        
    fhc_s = args.fhc_source
    bk_s = args.banking_source
    land_s = args.land_source
    cc_s = args.credit_source
    corp_s = args.corporate_source
    
    if args.sample:
        s_dir = base_dir / "data" / "samples"
        fhc_s = fhc_s or s_dir / "f10_fhc_setup_sample.csv"
        bk_s = bk_s or s_dir / "f10_banking12_sample.csv"
        land_s = land_s or s_dir / "f10_land_loan_sample.csv"
        cc_s = cc_s or s_dir / "f10_credit_card_sample.csv"
        corp_s = corp_s or s_dir / "f10_corporate_loan_sample.csv"
        
    result = run_f10_etl(
        target_db, 
        fhc_source=fhc_s, 
        banking_source=bk_s,
        land_source=land_s,
        credit_source=cc_s,
        corporate_source=corp_s
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
