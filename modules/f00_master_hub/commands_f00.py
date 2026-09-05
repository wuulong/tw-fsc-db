# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F00_SPECIFICATION.md"
manual = "README.md"
module = "f00_master_hub"
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

def search_global_entities(db_path: Path, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    透過全域 FTS5 倒排索引檢索跨模組實體 (支援 unicode61 前綴搜尋與 LIKE 降級相容)
    """
    if not db_path.exists() or not keyword:
        return []
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    clean_kw = keyword.replace('"', '').replace("'", "").strip()
    fts_query = f'"{clean_kw}"*'
    query_sql = """
        SELECT domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload,
               rank
        FROM fts_fsc_global
        WHERE fts_fsc_global MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        cursor.execute(query_sql, (fts_query, limit))
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            like_sql = """
                SELECT domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload, 0 as rank
                FROM fts_fsc_global
                WHERE primary_name LIKE ? OR secondary_info LIKE ?
                LIMIT ?
            """
            cursor.execute(like_sql, (f"%{clean_kw}%", f"%{clean_kw}%", limit))
            rows = [dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        like_sql = """
            SELECT domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload, 0 as rank
            FROM fts_fsc_global
            WHERE primary_name LIKE ? OR secondary_info LIKE ?
            LIMIT ?
        """
        cursor.execute(like_sql, (f"%{clean_kw}%", f"%{clean_kw}%", limit))
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
        
    return rows

def query_entity_360(db_path: Path, keyword: str) -> Optional[Dict[str, Any]]:
    """
    調閱單一機構的 360 度跨模組全景監理與營運檔案 (具備子表動態容錯能力)
    """
    if not db_path.exists() or not keyword:
        return None
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    kw = keyword.strip()
    
    # 嘗試從檢視表查詢，若底層表未全數建立則以 f00_entity_registry 為基準動態組裝
    try:
        cursor.execute("""
            SELECT * FROM v_f00_entity_360_profile
            WHERE canonical_name LIKE ? OR common_alias LIKE ? OR stock_code = ? OR tax_id = ?
            LIMIT 1
        """, (f"%{kw}%", f"%{kw}%", kw, kw))
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)
    except sqlite3.OperationalError:
        pass
        
    # 降級：從實體註冊表主動關聯既有存在的業務表
    cursor.execute("""
        SELECT master_uid, tax_id, stock_code, canonical_name, common_alias, entity_class, is_financial_institution, attributes_json
        FROM f00_entity_registry
        WHERE canonical_name LIKE ? OR common_alias LIKE ? OR stock_code = ? OR tax_id = ?
        LIMIT 1
    """, (f"%{kw}%", f"%{kw}%", kw, kw))
    ent = cursor.fetchone()
    if not ent:
        conn.close()
        return None
        
    res = dict(ent)
    c_name = res["canonical_name"]
    s_code = res.get("stock_code")
    
    # 嘗試抓取金控
    try:
        cursor.execute("SELECT group_assets_billion FROM f10_financial_holdings WHERE holding_name LIKE ? LIMIT 1", (f"%{c_name}%",))
        h_row = cursor.fetchone()
        res["fhc_assets_billion"] = h_row["group_assets_billion"] if h_row else None
    except sqlite3.OperationalError:
        res["fhc_assets_billion"] = None
        
    # 嘗試抓取銀行與信用資料 (F10)
    try:
        cursor.execute("SELECT loan_total, npl_ratio, coverage_ratio FROM f10_bank_asset_quality WHERE bank_name LIKE ? LIMIT 1", (f"%{c_name}%",))
        b_row = cursor.fetchone()
        res["bank_loan_total"] = b_row["loan_total"] if b_row else None
        res["bank_npl_ratio"] = b_row["npl_ratio"] if b_row else None
        res["bank_coverage_ratio"] = b_row["coverage_ratio"] if b_row else None
        
        # 土地融資
        cursor.execute("SELECT land_loan_balance, land_loan_ratio FROM f10_land_collateral_loans WHERE bank_name LIKE ? LIMIT 1", (f"%{c_name}%",))
        l_row = cursor.fetchone()
        res["bank_land_loan_balance"] = l_row["land_loan_balance"] if l_row else None
        res["bank_land_loan_ratio"] = l_row["land_loan_ratio"] if l_row else None
        
        # 信用卡
        cursor.execute("SELECT signing_amount_million, active_card_ratio FROM f10_credit_card_operations WHERE institution_name LIKE ? LIMIT 1", (f"%{c_name}%",))
        cc_row = cursor.fetchone()
        res["cc_signing_amount"] = cc_row["signing_amount_million"] if cc_row else None
        res["cc_active_card_ratio"] = cc_row["active_card_ratio"] if cc_row else None
    except sqlite3.OperationalError:
        res["bank_loan_total"] = None
        res["bank_npl_ratio"] = None
        res["bank_coverage_ratio"] = None
        res["bank_land_loan_balance"] = None
        res["bank_land_loan_ratio"] = None
        res["cc_signing_amount"] = None
        res["cc_active_card_ratio"] = None

    # 嘗試抓取營收與市場估值 (F20)
    try:
        if s_code:
            cursor.execute("SELECT current_month_revenue, yoy_growth_rate FROM f20_monthly_revenues WHERE company_code = ? LIMIT 1", (s_code,))
            r_row = cursor.fetchone()
            res["listed_monthly_revenue"] = r_row["current_month_revenue"] if r_row else None
            res["listed_revenue_yoy"] = r_row["yoy_growth_rate"] if r_row else None
            
            # 估值 P/E、殖利率
            cursor.execute("SELECT pe_ratio, dividend_yield, pb_ratio FROM f20_market_valuations WHERE company_code = ? LIMIT 1", (s_code,))
            v_row = cursor.fetchone()
            res["listed_pe_ratio"] = v_row["pe_ratio"] if v_row else None
            res["listed_dividend_yield"] = v_row["dividend_yield"] if v_row else None
            res["listed_pb_ratio"] = v_row["pb_ratio"] if v_row else None
        else:
            res["listed_monthly_revenue"] = None
            res["listed_revenue_yoy"] = None
            res["listed_pe_ratio"] = None
            res["listed_dividend_yield"] = None
            res["listed_pb_ratio"] = None
    except sqlite3.OperationalError:
        res["listed_monthly_revenue"] = None
        res["listed_revenue_yoy"] = None
        res["listed_pe_ratio"] = None
        res["listed_dividend_yield"] = None
        res["listed_pb_ratio"] = None

    conn.close()
    return res

def query_entity_relations(db_path: Path, keyword: str) -> Dict[str, Any]:
    """
    查詢單一實體之跨模組上下游控制力與股權拓樸關係 (包含作為母機構所屬子公司/轉投資，以及作為子機構所受控制/大股東)
    """
    if not db_path.exists() or not keyword:
        return {"entity": None, "subsidiaries": [], "parents_or_shareholders": []}
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    kw = keyword.strip()
    # 1. 尋找目標實體
    cursor.execute("""
        SELECT master_uid, canonical_name, common_alias, entity_class, stock_code
        FROM f00_entity_registry
        WHERE canonical_name LIKE ? OR common_alias LIKE ? OR stock_code = ? OR master_uid = ?
        LIMIT 1
    """, (f"%{kw}%", f"%{kw}%", kw, kw))
    target = cursor.fetchone()
    if not target:
        conn.close()
        return {"entity": None, "subsidiaries": [], "parents_or_shareholders": []}
        
    t_dict = dict(target)
    t_uid = t_dict["master_uid"]
    
    # 2. 查詢下游 (該實體作為 Parent 擁有的子公司 / 關係企業 / 被投資公司)
    cursor.execute("""
        SELECT r.relation_uid, r.relation_type, r.control_level, r.shareholding_ratio,
               c.master_uid AS related_uid, c.canonical_name AS related_name, c.entity_class AS related_class,
               c.stock_code AS related_stock_code
        FROM f00_entity_relations r
        JOIN f00_entity_registry c ON r.child_uid = c.master_uid
        WHERE r.parent_uid = ?
        ORDER BY r.shareholding_ratio DESC, c.canonical_name
    """, (t_uid,))
    subsidiaries = [dict(r) for r in cursor.fetchall()]
    
    # 3. 查詢上游 (該實體作為 Child 所屬母公司 / 金控集團 / 逾10%大股東)
    cursor.execute("""
        SELECT r.relation_uid, r.relation_type, r.control_level, r.shareholding_ratio,
               p.master_uid AS related_uid, p.canonical_name AS related_name, p.entity_class AS related_class,
               p.stock_code AS related_stock_code
        FROM f00_entity_relations r
        JOIN f00_entity_registry p ON r.parent_uid = p.master_uid
        WHERE r.child_uid = ?
        ORDER BY r.shareholding_ratio DESC, p.canonical_name
    """, (t_uid,))
    parents_or_shareholders = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "entity": t_dict,
        "subsidiaries": subsidiaries,
        "parents_or_shareholders": parents_or_shareholders
    }

