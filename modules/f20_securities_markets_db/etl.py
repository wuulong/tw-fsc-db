# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F20 證券期貨與公發公司開放資料清洗入庫 ETL (全面善用真實五大資料集與 SQLite 原生 UDFs)
category = etl
version = 2.1.0
"""

import os
import sys
import re
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

def run_f20_etl(db_path: Union[str, Path],
                isin_source: Union[str, Path] = None,
                revenue_source: Union[str, Path] = None,
                shareholder_source: Union[str, Path] = None,
                valuation_source: Union[str, Path] = None,
                futures_source: Union[str, Path] = None) -> Dict[str, Any]:
    """
    執行 F20 證券期貨與公開市場全量五大真實地面開放資料集清洗入庫
    優先讀取 data/raw 全量真實資料；支援指定 sample 供隔離測試
    """
    db_p = Path(db_path)
    db_p.parent.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    
    if not isin_source:
        isin_source = raw_dir / "f20_isin_companies.csv" if (raw_dir / "f20_isin_companies.csv").exists() else samples_dir / "f20_isin_companies_sample.csv"
    if not revenue_source:
        revenue_source = raw_dir / "f20_monthly_revenue_public.csv" if (raw_dir / "f20_monthly_revenue_public.csv").exists() else samples_dir / "f20_monthly_revenue_sample.csv"
    if not shareholder_source:
        shareholder_source = raw_dir / "f20_major_shareholders_listed.csv" if (raw_dir / "f20_major_shareholders_listed.csv").exists() else samples_dir / "f20_major_shareholders_sample.csv"
    if not valuation_source:
        valuation_source = raw_dir / "f23_market_valuation.csv" if (raw_dir / "f23_market_valuation.csv").exists() else samples_dir / "f20_market_valuation_sample.csv"
    if not futures_source:
        futures_source = raw_dir / "f24_futures_volume.csv" if (raw_dir / "f24_futures_volume.csv").exists() else samples_dir / "f20_futures_volume_sample.csv"
        
    conn = get_connection_with_udfs(db_p)
    cursor = conn.cursor()
    
    # 1. 確保載入本模組之 schema.sql
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    now_ts = datetime.now().isoformat()
    
    # 2. [F20-ADV-001] HTML 表格串流抽取並利用 UDF 下沉入庫 f20_companies
    isin_p = Path(isin_source)
    companies_count = 0
    if isin_p.exists():
        raw_b = isin_p.read_bytes()
        html_content = ""
        for enc in ["cp950", "big5", "utf-8", "utf-8-sig"]:
            try:
                html_content = raw_b.decode(enc)
                break
            except Exception:
                continue
            
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, re.DOTALL | re.IGNORECASE)
        current_market = "公開發行"
        raw_comp_rows = []
        for r in rows:
            tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL | re.IGNORECASE)
            td_texts = [re.sub(r"<[^>]+>", "", td).strip() for td in tds]
            if len(td_texts) == 1 and ("上市" in td_texts[0] or "上櫃" in td_texts[0] or "興櫃" in td_texts[0]):
                current_market = td_texts[0]
                continue
            if len(td_texts) >= 6:
                code_name = td_texts[0].split()
                if len(code_name) >= 2:
                    code = code_name[0].strip()
                    name = code_name[1].strip()
                    isin = td_texts[1].strip()
                    list_date = td_texts[2].strip()
                    market = td_texts[3].strip() or current_market
                    ind = td_texts[4].strip()
                    cfi = td_texts[5].strip() if len(td_texts) > 5 else ""
                    
                    if len(code) == 4 and code.isdigit():
                        raw_comp_rows.append((code, name, isin, list_date, market, ind, cfi, now_ts))
                        
        cursor.executemany("""
            INSERT OR REPLACE INTO f20_companies
            (company_code, company_name, isin_code, listing_date, market_type, industry_category, cfi_code, updated_at)
            VALUES (
                CLEAN_STR(?),
                CLEAN_STR(?),
                CLEAN_STR(?),
                ROC_TO_ISO(?),
                CLEAN_STR(?),
                CLEAN_STR(?),
                CLEAN_STR(?),
                ?
            )
        """, raw_comp_rows)
        companies_count = len(raw_comp_rows)

    # 3. [F20-ADV-002] 月營業收入彙總入庫 f20_monthly_revenues (利用 UDF: ROC_TO_ISO, PARSE_NUM)
    rev_p = Path(revenue_source)
    revenues_count = 0
    if rev_p.exists():
        with open(rev_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            raw_rev_rows = []
            for r in reader:
                code = r.get("公司代號", "")
                name = r.get("公司名稱", "")
                if not code or not name:
                    continue
                roc_ym = r.get("資料年月") or r.get("營業收入-營業收入年月", "")
                roc_date = r.get("出表日期", "")
                raw_rev_rows.append((
                    roc_ym,
                    code,
                    code,
                    name,
                    r.get("產業別", ""),
                    roc_ym,
                    roc_date,
                    r.get("營業收入-當月營收", ""),
                    r.get("營業收入-上月營收", ""),
                    r.get("營業收入-去年當月營收", ""),
                    r.get("營業收入-上月比較增減(%)", ""),
                    r.get("營業收入-去年同月增減(%)", ""),
                    r.get("累計營業收入-當月累計營收", ""),
                    r.get("累計營業收入-去年累計營收", ""),
                    r.get("累計營業收入-前期比較增減(%)", ""),
                    r.get("備註", ""),
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f20_monthly_revenues
                (revenue_uid, company_code, company_name, industry_name, revenue_year_month, report_date,
                 current_month_revenue, last_month_revenue, last_year_same_month_revenue,
                 mom_growth_rate, yoy_growth_rate, cum_current_revenue, cum_last_year_revenue, cum_yoy_growth_rate,
                 note, updated_at)
                VALUES (
                    'REV_' || ROC_TO_ISO(?) || '_' || ?,
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    ROC_TO_ISO(?),
                    ROC_TO_ISO(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    CLEAN_STR(?),
                    ?
                )
            """, raw_rev_rows)
            revenues_count = len(raw_rev_rows)

    # 4. [F20-ADV-004] 大股東申報表入庫 f20_major_shareholders (利用 UDF: ENTITY_MD5, ROC_TO_ISO)
    sh_p = Path(shareholder_source)
    shareholders_count = 0
    if sh_p.exists():
        with open(sh_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            raw_sh_rows = []
            for r in reader:
                code = r.get("公司代號", "")
                c_name = r.get("公司名稱", "")
                sh_name = r.get("大股東名稱", "")
                if not code or not sh_name:
                    continue
                is_corp = 1 if any(k in sh_name for k in ["公司", "銀行", "法人", "投資", "信託", "基金"]) else 0
                rep_date = r.get("出表日期", "")
                raw_sh_rows.append((
                    code,
                    sh_name,
                    code,
                    c_name,
                    sh_name,
                    rep_date,
                    is_corp,
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f20_major_shareholders
                (shareholder_uid, company_code, company_name, shareholder_name, report_date, is_corporate, updated_at)
                VALUES (
                    'SH_' || ? || '_' || ENTITY_MD5(?),
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    ROC_TO_ISO(?),
                    ?,
                    ?
                )
            """, raw_sh_rows)
            shareholders_count = len(raw_sh_rows)

    # 5. [F20-ADV-005] 上櫃股票本益比/殖利率/淨值比入庫 f20_market_valuations (支援 cp950/big5/utf-8)
    val_p = Path(valuation_source)
    valuations_count = 0
    if val_p.exists():
        val_bytes = val_p.read_bytes()
        val_text = None
        for enc in ["cp950", "big5", "utf-8-sig", "utf-8"]:
            try:
                val_text = val_bytes.decode(enc)
                break
            except Exception:
                continue
                
        if val_text:
            lines = [l for l in val_text.splitlines() if l.strip()]
            data_date = "2026-09-04"
            # 尋找日期行 "資料日期:115/09/04"
            for l in lines[:5]:
                if "資料日期" in l:
                    parts = l.split(":")
                    if len(parts) >= 2:
                        raw_d = parts[1].strip()
                        # ROC 115/09/04 -> 2026-09-04
                        dp = raw_d.split("/")
                        if len(dp) == 3:
                            data_date = f"{int(dp[0])+1911}-{dp[1].zfill(2)}-{dp[2].zfill(2)}"
            
            # 從標題行開始解析
            start_idx = 0
            for i, l in enumerate(lines[:10]):
                if "股票代號" in l and "本益比" in l:
                    start_idx = i
                    break
                    
            reader = csv.DictReader(lines[start_idx:])
            raw_val_rows = []
            for r in reader:
                code = r.get("股票代號", "")
                name = r.get("公司名稱", "")
                if not code or not name or not code.strip().isalnum():
                    continue
                code = code.strip().replace('"', '')
                name = name.strip().replace('"', '')
                raw_val_rows.append((
                    data_date,
                    code,
                    code,
                    name,
                    r.get("本益比", "0"),
                    r.get("殖利率(%)", "0"),
                    r.get("股價淨值比", "0"),
                    r.get("每股股利(註)", "0"),
                    r.get("股利年度", ""),
                    r.get("財報年/季", ""),
                    data_date,
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f20_market_valuations
                (valuation_uid, company_code, company_name, pe_ratio, dividend_yield, pb_ratio, dividend_per_share, dividend_year, report_quarter, trade_date, updated_at)
                VALUES (
                    'VAL_' || ? || '_' || ?,
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    PARSE_NUM(?),
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    ?,
                    ?
                )
            """, raw_val_rows)
            valuations_count = len(raw_val_rows)

    # 6. [F20-ADV-006] 期交所期貨交易量與未平倉合約入庫 f20_futures_trading
    fut_p = Path(futures_source)
    futures_count = 0
    if fut_p.exists():
        with open(fut_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            raw_fut_rows = []
            for r in reader:
                code = r.get("契約代號", "")
                name = r.get("契約名稱", "")
                if not code or not name or "HTML" in code:
                    continue
                raw_fut_rows.append((
                    code.strip(),
                    name.strip(),
                    r.get("交易月份", "2026-08").strip(),
                    r.get("成交量[口]", "0"),
                    r.get("日均成交量[口]", "0"),
                    r.get("未平倉量[口]", "0"),
                    r.get("交易契約價值[百萬元]", "0"),
                    now_ts
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO f20_futures_trading
                (contract_code, contract_name, trade_month, total_volume, daily_avg_volume, open_interest, contract_value_million, updated_at)
                VALUES (
                    CLEAN_STR(?),
                    CLEAN_STR(?),
                    ?,
                    CAST(PARSE_NUM(?) AS INTEGER),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    CAST(PARSE_NUM(?) AS INTEGER),
                    PARSE_NUM(?),
                    ?
                )
            """, raw_fut_rows)
            futures_count = len(raw_fut_rows)
            
    conn.commit()
    conn.close()
    
    # 7. 登記 F20 子模組元資料 (sys_module_metadata)
    tables_meta = [
        ("f20_companies", companies_count),
        ("f20_monthly_revenues", revenues_count),
        ("f20_major_shareholders", shareholders_count),
        ("f20_market_valuations", valuations_count),
        ("f20_futures_trading", futures_count)
    ]
    for tbl, cnt in tables_meta:
        register_submodule_metadata(
            db_p,
            module_id="f20_securities_markets_db",
            module_name="證券期貨與公開市場資料庫",
            table_name=tbl,
            schema_version="2.1.0",
            record_count=cnt
        )
    
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "companies_loaded": companies_count,
        "revenues_loaded": revenues_count,
        "shareholders_loaded": shareholders_count,
        "valuations_loaded": valuations_count,
        "futures_loaded": futures_count,
        "total_records": companies_count + revenues_count + shareholders_count + valuations_count + futures_count,
        "executed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F20 子模組自包含 ETL 入庫腳本 (五大真實開放資料 + 原生 UDFs)")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    parser.add_argument("--isin-source", default=None, help="ISIN 公司名冊路徑")
    parser.add_argument("--revenue-source", default=None, help="月營收彙總路徑")
    parser.add_argument("--shareholder-source", default=None, help="大股東名單路徑")
    parser.add_argument("--valuation-source", default=None, help="市場估值本益比路徑")
    parser.add_argument("--futures-source", default=None, help="期貨交易量年報路徑")
    parser.add_argument("--sample", action="store_true", help="強制使用 samples 目錄資料 (供測試使用)")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    if not args.db:
        target_db = base_dir / "db" / "fsc.db"
    else:
        target_db = Path(args.db)
        
    isin_s = args.isin_source
    rev_s = args.revenue_source
    sh_s = args.shareholder_source
    val_s = args.valuation_source
    fut_s = args.futures_source
    
    if args.sample:
        s_dir = base_dir / "data" / "samples"
        isin_s = isin_s or s_dir / "f20_isin_companies_sample.csv"
        rev_s = rev_s or s_dir / "f20_monthly_revenue_sample.csv"
        sh_s = sh_s or s_dir / "f20_major_shareholders_sample.csv"
        val_s = val_s or s_dir / "f20_market_valuation_sample.csv"
        fut_s = fut_s or s_dir / "f20_futures_volume_sample.csv"
        
    result = run_f20_etl(
        target_db,
        isin_source=isin_s,
        revenue_source=rev_s,
        shareholder_source=sh_s,
        valuation_source=val_s,
        futures_source=fut_s
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
