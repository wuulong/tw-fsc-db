# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F10_SPECIFICATION.md"
manual = "README.md"
module = "f10_banking_credit_db"
version = "2.1.0"
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

# 引用母模組 a00_core 通用函式庫與 UDFs
src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from a00_core.udfs import get_connection_with_udfs

def query_financial_holdings(db_path: Path, limit: int = 10, min_assets: float = 0.0) -> List[Dict[str, Any]]:
    """查詢金融控股公司與資產規模"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT holding_name, approved_date, opening_date, group_assets_billion, group_net_worth_billion, subsidiaries_count, subsidiaries_text
        FROM f10_financial_holdings
        WHERE group_assets_billion >= ?
        ORDER BY group_assets_billion DESC
        LIMIT ?
    """, (min_assets, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_bank_asset_quality(db_path: Path, limit: int = 10, max_npl: Optional[float] = None) -> List[Dict[str, Any]]:
    """查詢本國銀行資產品質 (逾放比、備抵呆帳)"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    if max_npl is not None:
        cursor.execute("""
            SELECT bank_name, deposit_amount, pretax_profit, loan_total, npl_ratio, coverage_ratio
            FROM f10_bank_asset_quality
            WHERE npl_ratio <= ?
            ORDER BY loan_total DESC
            LIMIT ?
        """, (max_npl, limit))
    else:
        cursor.execute("""
            SELECT bank_name, deposit_amount, pretax_profit, loan_total, npl_ratio, coverage_ratio
            FROM f10_bank_asset_quality
            ORDER BY loan_total DESC
            LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_land_collateral_loans(db_path: Path, limit: int = 10, min_ratio: float = 0.0) -> List[Dict[str, Any]]:
    """查詢銀行土地擔保放款餘額與集中度 (銀行法 72-2 條關聯)"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bank_name, land_loan_balance, total_loan_including_call, land_loan_ratio
        FROM f10_land_collateral_loans
        WHERE land_loan_ratio >= ?
        ORDER BY land_loan_balance DESC
        LIMIT ?
    """, (min_ratio, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_credit_card_operations(db_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """查詢銀行信用卡發卡與簽帳營運資料"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT institution_name, cards_effective, cards_active, active_card_ratio, signing_amount_million, revolving_balance_million, delinquent_over_3m_million
        FROM f10_credit_card_operations
        ORDER BY signing_amount_million DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_corporate_loan_trends(db_path: Path, limit: int = 12) -> List[Dict[str, Any]]:
    """查詢全台企業總貸款月度趨勢與平均額度"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year_month, loan_entity_count, loan_total_billion, loan_avg_thousand
        FROM f10_corporate_loan_trends
        ORDER BY year_month DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_bank_credit_risk_radar(db_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """查詢銀行信用風險綜合監理雷達 (含 UDF RISK_BADGE 燈號)"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bank_name, loan_total, npl_ratio, coverage_ratio, land_loan_ratio, cc_monthly_signing, supervisory_risk_badge
        FROM v_f10_bank_credit_risk_profile
        ORDER BY loan_total DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_holding_banking_summary(db_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """查詢金控與旗下銀行聯動檢視表"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM v_f10_holding_banking_summary
        ORDER BY group_assets_billion DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows