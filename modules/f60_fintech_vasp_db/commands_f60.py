# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F60_SPECIFICATION.md"
advanced_spec = "F60_ADVANCED_SPEC.md"
manual = "README.md"
module = "f60_fintech_vasp_db"
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

def query_vasp_registry(db_path: Path, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    查詢虛擬資產平台業者 (VASP) 洗錢防制法遵名冊
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cur = conn.cursor()
    if status:
        cur.execute("""
            SELECT vasp_id, brand_name, company_name, tax_id, compliance_date,
                   business_type, fiat_custody_bank, status, updated_at
            FROM f60_vasp_compliance_registry
            WHERE status = ?
            ORDER BY compliance_date ASC
            LIMIT ?;
        """, (status, limit))
    else:
        cur.execute("""
            SELECT vasp_id, brand_name, company_name, tax_id, compliance_date,
                   business_type, fiat_custody_bank, status, updated_at
            FROM f60_vasp_compliance_registry
            ORDER BY compliance_date ASC
            LIMIT ?;
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def query_fintech_sandbox(db_path: Path, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    查詢金融科技監理沙盒與創新實驗專案
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cur = conn.cursor()
    if status:
        cur.execute("""
            SELECT case_no, applicant, partner_institution, partner_tax_id,
                   experiment_title, experiment_domain, approval_date, status, updated_at
            FROM f60_fintech_sandbox
            WHERE status = ?
            ORDER BY approval_date ASC
            LIMIT ?;
        """, (status, limit))
    else:
        cur.execute("""
            SELECT case_no, applicant, partner_institution, partner_tax_id,
                   experiment_title, experiment_domain, approval_date, status, updated_at
            FROM f60_fintech_sandbox
            ORDER BY approval_date ASC
            LIMIT ?;
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def query_greenhouse_gas_trends(db_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """
    查詢國家溫室氣體歷年排放時序與淨排碳指標
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT year, co2_value, ch4_value, n2o_value, total_ghg_emission_value,
               co2_absorption_value, net_ghg_emission_value
        FROM f60_greenhouse_gas_report
        ORDER BY year DESC
        LIMIT ?;
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def penetrate_sandbox_partner_institution(db_path: Path, query_key: str) -> Optional[Dict[str, Any]]:
    """
    [F60-ADV-FSC-001] 新創沙盒 ➔ 合作傳統特許銀行體質穿透
    依沙盒案號或申請新創名稱，穿透合作特許銀行之營運品質與資產規模
    """
    if not db_path.exists():
        return None
    conn = get_connection_with_udfs(db_path)
    cur = conn.cursor()
    
    # 1. 查找沙盒實驗案
    cur.execute("""
        SELECT case_no, applicant, partner_institution, partner_tax_id,
               experiment_title, experiment_domain, approval_date, status
        FROM f60_fintech_sandbox
        WHERE case_no = ? OR applicant LIKE ? OR partner_institution LIKE ?
        LIMIT 1;
    """, (query_key, f"%{query_key}%", f"%{query_key}%"))
    sandbox_row = cur.fetchone()
    if not sandbox_row:
        conn.close()
        return None
    sandbox_info = dict(sandbox_row)
    partner_bank = sandbox_info["partner_institution"]
    
    # 2. 穿透 F10 銀行營運與資產品質
    cur.execute("""
        SELECT bank_name, deposit_amount, pretax_profit, loan_total,
               overdue_loan_total, npl_ratio, coverage_ratio
        FROM f10_bank_asset_quality
        WHERE bank_name LIKE ? OR ? LIKE '%' || bank_name || '%'
        LIMIT 1;
    """, (f"%{partner_bank}%", partner_bank))
    bank_row = cur.fetchone()
    bank_info = dict(bank_row) if bank_row else None
    
    # 3. 穿透 F50 該銀行歷史裁罰案
    cur.execute("""
        SELECT sanction_uid, doc_no, sanction_date, target_name, penalty_fine_ntd, main_subject
        FROM f50_sanctions
        WHERE target_name LIKE ? OR ? LIKE '%' || target_name || '%'
        ORDER BY sanction_date DESC
        LIMIT 3;
    """, (f"%{partner_bank}%", partner_bank))
    sanctions_list = [dict(r) for r in cur.fetchall()]
    
    conn.close()
    return {
        "sandbox_case": sandbox_info,
        "partner_bank_asset_quality": bank_info,
        "partner_bank_recent_sanctions": sanctions_list
    }

def query_vasp_aml_sanctions_synergy(db_path: Path, keyword: str = "虛擬") -> List[Dict[str, Any]]:
    """
    [F60-ADV-FSC-002] 傳統銀行之虛擬通貨 (VASP) 監控裁罰聯防
    檢索歷史重大裁罰中涉及虛擬通貨、洗錢防制監控缺失之裁罰案例
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT sanction_uid, doc_no, sanction_date, target_name, penalty_fine_ntd, main_subject, violation_facts
        FROM f50_sanctions
        WHERE violation_facts LIKE ? OR main_subject LIKE ?
        ORDER BY sanction_date DESC
        LIMIT 10;
    """, (f"%{keyword}%", f"%{keyword}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
