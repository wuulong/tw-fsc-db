# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F30_SPECIFICATION.md"
manual = "README.md"
module = "f30_insurance_actuarial_db"
version = "2.0.0"
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

def query_insurance_institutions(
    db_path: Path,
    limit: int = 20,
    institution_type: Optional[str] = None,
    order_by: str = "actuary_count"
) -> List[Dict[str, Any]]:
    """查詢保險機構人力配置與精算人員統計"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    
    valid_cols = {"actuary_count", "underwriting_count", "claim_count", "inner_staff_count", "field_agent_count", "insurer_name"}
    sort_col = order_by if order_by in valid_cols else "actuary_count"
    
    if institution_type:
        cursor.execute(f"""
            SELECT insurer_name, insurer_type, inner_staff_count, field_agent_count, underwriting_count, claim_count, actuary_count, report_date
            FROM f30_insurance_institutions
            WHERE insurer_type = ?
            ORDER BY {sort_col} DESC
            LIMIT ?
        """, (institution_type, limit))
    else:
        cursor.execute(f"""
            SELECT insurer_name, insurer_type, inner_staff_count, field_agent_count, underwriting_count, claim_count, actuary_count, report_date
            FROM f30_insurance_institutions
            ORDER BY {sort_col} DESC
            LIMIT ?
        """, (limit,))
        
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_complaint_trends(db_path: Path, limit: int = 15) -> List[Dict[str, Any]]:
    """查詢歷年保險消費爭議與申訴解決趨勢"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT eval_year, policy_contract_thousand, complaint_count, complaint_ratio, settlement_count, settlement_ratio, complainant_favored_ratio
        FROM f30_insurance_complaint_trends
        ORDER BY eval_year DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_compensation_fund(db_path: Path, limit: int = 15) -> List[Dict[str, Any]]:
    """查詢汽車交通事故特別補償基金運作與每案平均給付金額"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stat_year, contribution_income_thousand, compensation_expense_thousand, compensated_cases, avg_compensation_thousand
        FROM f30_special_compensation_fund
        ORDER BY stat_year DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_holding_insurer_summary(db_path: Path, limit: int = 15) -> List[Dict[str, Any]]:
    """查詢金控集團旗下保險公司及其核保精算資源佈局"""
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM v_f30_holding_insurer_summary
        ORDER BY group_assets_billion DESC, actuary_count DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
