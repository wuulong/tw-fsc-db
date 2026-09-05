# -*- coding: utf-8 -*-
"""
[metadata]
name: udfs.py
title: 金管會資料庫 (tw-fsc-db) 全域 SQLite 使用者自訂函數 (UDFs) 註冊工廠
description: 提供統一的 SQLite UDF 下沉封裝，簡化 SQL 查詢與 ETL，杜絕 Python 端重型字串迴圈處理。
category: core
version: 1.0.0
"""

import re
import sqlite3
import hashlib
from typing import Optional, Any
from a00_core.utils.date_parser import parse_taiwan_date_universal
from a00_core.utils.cleaners import safe_float, safe_int, clean_text
from a00_core.utils.identity_resolver import validate_tax_id

def roc_to_iso(val: Any) -> str:
    """UDF: 民國年/西元年萬用轉換為 ISO-8601 (YYYY-MM-DD 或 YYYY-MM)"""
    return parse_taiwan_date_universal(val)

def parse_num(val: Any) -> float:
    """UDF: 安全解析浮點數，去除千分位逗號、空白、負數正負號保留"""
    return safe_float(val, 0.0)

def clean_str(val: Any) -> str:
    """UDF: 清洗字串，消除連續空白與全形空白"""
    return clean_text(val)

def valid_tax_id(val: Any) -> int:
    """UDF: 8 碼統一編號校驗 (符合回傳 1，不符回傳 0)"""
    return 1 if validate_tax_id(str(val)) else 0

def count_delimited(val: Any, delimiter: str = "、") -> int:
    """UDF: 計算特定分隔符號分割後的非空專案數量"""
    if not val:
        return 0
    s = str(val).replace("、", ",").replace(";", ",")
    items = [x.strip() for x in s.split(",") if x.strip()]
    return len(items)

def calc_yoy_growth(current: Any, previous: Any) -> float:
    """UDF: 計算成長率 YoY (%)，自動除以零防呆"""
    c = safe_float(current, 0.0)
    p = safe_float(previous, 0.0)
    if p == 0.0:
        return 0.0
    return round((c - p) / abs(p) * 100.0, 2)

def bank_72_2_ratio(real_estate_loan: Any, total_deposit: Any) -> float:
    """UDF: 銀行法第 72-2 條不動產放款比率 (%)"""
    loan = safe_float(real_estate_loan, 0.0)
    dep = safe_float(total_deposit, 0.0)
    if dep <= 0.0:
        return 0.0
    return round(loan / dep * 100.0, 2)

def risk_badge(npl_ratio: Any, coverage_ratio: Any) -> str:
    """UDF: 銀行資產品質綜合預警燈號 (GREEN, YELLOW, RED)"""
    npl = safe_float(npl_ratio, 0.0)
    cov = safe_float(coverage_ratio, 0.0)
    if npl > 0.5 or (cov > 0 and cov < 300.0):
        return "RED"
    elif npl > 0.2 or (cov > 0 and cov < 600.0):
        return "YELLOW"
    return "GREEN"

def entity_md5(name: Any) -> str:
    """UDF: 決定性 MD5 實體雜湊摘要前 8 碼"""
    if not name:
        return "00000000"
    return hashlib.md5(str(name).strip().encode("utf-8")).hexdigest()[:8]

def register_fsc_udfs(conn: sqlite3.Connection) -> None:
    """
    將全套金融監理 UDF 下沉註冊至 SQLite 連線中
    """
    # 1. 日期與數值清洗 UDF
    conn.create_function("ROC_TO_ISO", 1, roc_to_iso)
    conn.create_function("PARSE_NUM", 1, parse_num)
    conn.create_function("CLEAN_STR", 1, clean_str)
    
    # 2. 身份與字串分析 UDF
    conn.create_function("VALID_TAX_ID", 1, valid_tax_id)
    conn.create_function("COUNT_DELIMITED", 1, lambda s: count_delimited(s, "、"))
    conn.create_function("COUNT_DELIMITED", 2, count_delimited)
    conn.create_function("ENTITY_MD5", 1, entity_md5)
    
    # 3. 領域業務特徵與風控指標 UDF
    conn.create_function("CALC_YOY", 2, calc_yoy_growth)
    conn.create_function("BANK_72_2_RATIO", 2, bank_72_2_ratio)
    conn.create_function("RISK_BADGE", 2, risk_badge)

def get_connection_with_udfs(db_path: Any) -> sqlite3.Connection:
    """便利工廠函式：開啟 SQLite 連線並自動注入所有全域 UDF"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    register_fsc_udfs(conn)
    return conn
