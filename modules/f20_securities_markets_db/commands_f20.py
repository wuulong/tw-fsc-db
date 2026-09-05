# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F20_SPECIFICATION.md"
manual = "README.md"
module = "f20_securities_markets_db"
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

def query_top_revenue_companies(db_path: Path, limit: int = 10, min_yoy: Optional[float] = None) -> List[Dict[str, Any]]:
    """查詢當月營收最高或 YoY 年增率最高的上市公司"""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if min_yoy is not None:
        cursor.execute("""
            SELECT company_code, company_name, industry_name, revenue_year_month, current_month_revenue, yoy_growth_rate
            FROM f20_monthly_revenues
            WHERE yoy_growth_rate >= ?
            ORDER BY yoy_growth_rate DESC
            LIMIT ?
        """, (min_yoy, limit))
    else:
        cursor.execute("""
            SELECT company_code, company_name, industry_name, revenue_year_month, current_month_revenue, yoy_growth_rate
            FROM f20_monthly_revenues
            ORDER BY current_month_revenue DESC
            LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_company_profile(db_path: Path, query_term: str) -> Optional[Dict[str, Any]]:
    """一鍵查詢公司基本面、最新月營收與大股東名冊 (透過檢視表 v_f20_company_revenue_profile)"""
    if not db_path.exists() or not query_term:
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM v_f20_company_revenue_profile
        WHERE company_code = ? OR company_name LIKE ?
        LIMIT 1
    """, (query_term, f"%{query_term}%"))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def query_major_shareholders(db_path: Path, query_term: str) -> List[Dict[str, Any]]:
    """查詢特定公司之 10% 大股東申報名冊"""
    if not db_path.exists() or not query_term:
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_code, company_name, shareholder_name, is_corporate, report_date
        FROM f20_major_shareholders
        WHERE company_code = ? OR company_name LIKE ?
        ORDER BY shareholder_name
    """, (query_term, f"%{query_term}%"))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_market_valuations(db_path: Path, limit: int = 10, min_yield: Optional[float] = None, max_pe: Optional[float] = None) -> List[Dict[str, Any]]:
    """查詢股票市場估值 (本益比 P/E、殖利率、股價淨值比 P/B)"""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    conditions = ["pe_ratio > 0"]
    params = []
    if min_yield is not None:
        conditions.append("dividend_yield >= ?")
        params.append(min_yield)
    if max_pe is not None:
        conditions.append("pe_ratio <= ?")
        params.append(max_pe)
        
    where_clause = " WHERE " + " AND ".join(conditions)
    params.append(limit)
    cursor.execute(f"""
        SELECT company_code, company_name, pe_ratio, dividend_yield, pb_ratio, dividend_per_share, report_quarter, trade_date
        FROM f20_market_valuations
        {where_clause}
        ORDER BY dividend_yield DESC
        LIMIT ?
    """, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_futures_trading(db_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """查詢期交所主力商品交易量與未平倉合約口數"""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT contract_code, contract_name, trade_month, total_volume, daily_avg_volume, open_interest, contract_value_million
        FROM f20_futures_trading
        ORDER BY total_volume DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
