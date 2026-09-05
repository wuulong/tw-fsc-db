# -*- coding: utf-8 -*-
"""
[metadata]
spec = "F50_SPECIFICATION.md"
manual = "README.md"
module = "f50_sanctions_legal_db"
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

def search_sanctions(
    db_path: Path,
    keyword: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    透過 FTS5 全文倒排檢索金融處分案 (字號、受處分人、事實、法令)
    """
    if not db_path.exists() or not keyword:
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    
    clean_kw = keyword.replace('"', '').replace("'", "").strip()
    query = """
        SELECT s.sanction_uid, s.doc_no, s.sanction_date, s.target_name, s.tax_id,
               s.penalty_fine_ntd, s.agency_bureau, s.main_subject, s.violation_facts, s.legal_basis
        FROM f50_sanctions_fts fts
        JOIN f50_sanctions s ON fts.sanction_uid = s.sanction_uid
        WHERE f50_sanctions_fts MATCH ?
        ORDER BY s.sanction_date DESC
        LIMIT ?
    """
    params = [f'"{clean_kw}"*', limit]
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    
    # 若 FTS5 未命中則 fallback 至 LIKE
    if not rows:
        like_query = """
            SELECT sanction_uid, doc_no, sanction_date, target_name, tax_id,
                   penalty_fine_ntd, agency_bureau, main_subject, violation_facts, legal_basis
            FROM f50_sanctions
            WHERE (target_name LIKE ? OR doc_no LIKE ? OR main_subject LIKE ? OR violation_facts LIKE ? OR legal_basis LIKE ?)
            ORDER BY sanction_date DESC
            LIMIT ?
        """
        lk = f"%{clean_kw}%"
        cursor.execute(like_query, (lk, lk, lk, lk, lk, limit))
        rows = [dict(r) for r in cursor.fetchall()]
        
    conn.close()
    return rows

def query_top_penalized_institutions(
    db_path: Path,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    查詢歷史累計裁罰次數與累計罰鍰總額排行
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT target_name, total_sanctions_count, total_penalty_fine_ntd, latest_sanction_date
        FROM v_f50_institution_sanction_summary
        WHERE target_name != '受處分金融機構'
        ORDER BY total_penalty_fine_ntd DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def query_ombudsman_disputes(
    db_path: Path,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    查詢金融消費評議中心銀行業爭議申訴統計排行
    """
    if not db_path.exists():
        return []
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT institution_name, complaint_count, complaint_ratio, start_date, end_date
        FROM f50_ombudsman_cases
        ORDER BY complaint_count DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def track_deficiency_to_sanction_escalation(
    db_path: Path,
    keyword: str
) -> Dict[str, Any]:
    """
    [F50-ADV-FSC-001] 重大缺失 ➔ 監理裁罰升級演進追蹤 (Deficiency-to-Sanction Escalation Tracker)
    依關鍵字關聯 F40 檢查缺失情節與 F50 正式裁處事實，建立歷史演進檢視
    """
    if not db_path.exists() or not keyword:
        return {"keyword": keyword, "exam_deficiencies": [], "formal_sanctions": []}
        
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    
    clean_kw = keyword.strip()
    
    # 1. 檢索 F40 缺失
    cursor.execute("""
        SELECT deficiency_uid, target_sector, eval_year, half_year,
               business_category, deficiency_pattern, deficiency_detail, improvement_action
        FROM f40_exam_deficiencies
        WHERE deficiency_pattern LIKE ? OR deficiency_detail LIKE ?
        ORDER BY eval_year DESC
        LIMIT 5
    """, (f"%{clean_kw}%", f"%{clean_kw}%"))
    deficiencies = [dict(r) for r in cursor.fetchall()]
    
    # 2. 檢索 F50 裁罰
    cursor.execute("""
        SELECT sanction_uid, doc_no, sanction_date, target_name, penalty_fine_ntd, main_subject, violation_facts
        FROM f50_sanctions
        WHERE target_name LIKE ? OR main_subject LIKE ? OR violation_facts LIKE ?
        ORDER BY sanction_date DESC
        LIMIT 5
    """, (f"%{clean_kw}%", f"%{clean_kw}%", f"%{clean_kw}%"))
    sanctions = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "keyword": clean_kw,
        "deficiencies_found": len(deficiencies),
        "sanctions_found": len(sanctions),
        "exam_deficiencies": deficiencies,
        "formal_sanctions": sanctions
    }

def sync_sanctions_to_supervisory_radar(db_path: Path) -> Dict[str, Any]:
    """
    [F50-ADV-FSC-002] 裁罰總額注入 F00 監理綜合風險雷達
    將各受罰機構之真實歷史累計裁罰次數與累計罰鍰即時回寫入 f00_supervisory_radar
    """
    if not db_path.exists():
        return {"status": "FAILED", "reason": "db_not_found"}
        
    conn = get_connection_with_udfs(db_path)
    cursor = conn.cursor()
    
    # 查詢各機構裁罰統計
    cursor.execute("""
        SELECT target_name, total_sanctions_count, total_penalty_fine_ntd
        FROM v_f50_institution_sanction_summary
        WHERE target_name != '受處分金融機構'
    """)
    sanction_stats = cursor.fetchall()
    
    updated_records = 0
    now_ts = "2026-09-05T12:00:00"
    eval_ym = "2026-09"
    
    for row in sanction_stats:
        t_name = row["target_name"]
        s_count = row["total_sanctions_count"]
        fine_ntd = row["total_penalty_fine_ntd"]
        
        # 尋找對應之 f00_entity_registry 實體
        cursor.execute("""
            SELECT master_uid, canonical_name, entity_class
            FROM f00_entity_registry
            WHERE canonical_name LIKE ? OR common_alias LIKE ?
            LIMIT 1
        """, (f"%{t_name[:4]}%", f"%{t_name[:4]}%"))
        ent = cursor.fetchone()
        if not ent:
            continue
            
        uid = ent["master_uid"]
        radar_uid = f"RDR_{uid}_{eval_ym}"
        
        # 檢查雷達中是否已有該實體紀錄
        cursor.execute("SELECT exam_deficiency_count, npl_ratio FROM f00_supervisory_radar WHERE radar_uid = ?", (radar_uid,))
        existing = cursor.fetchone()
        def_cnt = existing["exam_deficiency_count"] if existing else 3
        npl_val = existing["npl_ratio"] if existing else 0.15
        
        # 綜合判定風險燈號 (若罰鍰 > 2000 萬或缺失 >= 8 為 RED; 罰鍰 > 500 萬或缺失 >= 4 為 YELLOW; 否則 GREEN)
        if fine_ntd >= 20000000.0 or def_cnt >= 8:
            risk_level = "RED"
        elif fine_ntd >= 5000000.0 or def_cnt >= 4:
            risk_level = "YELLOW"
        else:
            risk_level = "GREEN"
            
        cursor.execute("""
            INSERT OR REPLACE INTO f00_supervisory_radar
            (radar_uid, entity_uid, eval_year_month, total_sanctions_count, total_penalty_fine_ntd,
             exam_deficiency_count, consumer_dispute_count, npl_ratio, revenue_growth_yoy, composite_risk_level, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0.0, ?, ?)
        """, (radar_uid, uid, eval_ym, s_count, fine_ntd, def_cnt, npl_val, risk_level, now_ts))
        updated_records += 1
        
    conn.commit()
    conn.close()
    
    return {
        "status": "SUCCESS",
        "eval_year_month": eval_ym,
        "radar_records_updated": updated_records
    }
