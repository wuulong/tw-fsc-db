# -*- coding: utf-8 -*-
"""
F50 單元測試腳本：涵蓋 F50_TEST_PLAN.md 中 [TCV-F50-001] ~ [TCV-F50-006]
包含處分書 XML 解析、FTS5 全文倒排檢索、排行榜檢視、評議案件與進階演進追蹤及雷達同步。
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

module_dir = Path(__file__).resolve().parent.parent
base_dir = module_dir.parent.parent
src_dir = base_dir / "src"
sys.path.insert(0, str(module_dir))
sys.path.insert(0, str(src_dir))

from etl import run_f50_etl
from commands_f50 import (
    search_sanctions,
    query_top_penalized_institutions,
    query_ombudsman_disputes,
    track_deficiency_to_sanction_escalation,
    sync_sanctions_to_supervisory_radar
)

def test_f50_full_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_p = Path(tmp_db.name)
        
    try:
        # [TCV-F50-001] 自包含隔離建表與 ETL
        res = run_f50_etl(db_path=tmp_db_p)
        assert res["status"] == "SUCCESS", "[TCV-F50-001] ETL 執行失敗"
        assert res["sanctions_loaded"] >= 450, "[TCV-F50-001] 處分書載入數不足 450"
        assert res["ombudsman_cases_loaded"] >= 15, "[TCV-F50-001] 評議案件載入數不足 15"
        
        # [TCV-F50-002] 罰鍰金額解析校驗
        conn = sqlite3.connect(str(tmp_db_p))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT penalty_fine_ntd FROM f50_sanctions WHERE doc_no LIKE '%11502721972%'")
        row = c.fetchone()
        assert row is not None, "[TCV-F50-002] 查無合庫信用卡處分書"
        assert row["penalty_fine_ntd"] == 12000000.0, "[TCV-F50-002] 罰鍰金額解析不符 12,000,000"
        conn.close()
        
        # [TCV-F50-003] FTS5 全文倒排檢索
        s_res = search_sanctions(tmp_db_p, "信用卡疑義帳款")
        assert len(s_res) >= 1, "[TCV-F50-003] FTS5 檢索無結果"
        assert "合作金庫" in s_res[0]["target_name"]
        
        # [TCV-F50-004] 裁罰排行榜檢視
        top_insts = query_top_penalized_institutions(tmp_db_p, limit=5)
        assert len(top_insts) == 5, "[TCV-F50-004] 排行筆數不足"
        assert top_insts[0]["total_penalty_fine_ntd"] >= top_insts[1]["total_penalty_fine_ntd"]
        
        # [TCV-F50-005] 金融消費評議申訴查詢
        disputes = query_ombudsman_disputes(tmp_db_p, limit=5)
        assert len(disputes) == 5, "[TCV-F50-005] 爭議申訴查詢筆數不足"
        assert disputes[0]["complaint_count"] >= disputes[1]["complaint_count"]
        
        print("✅ F50 基礎 5 大測試案例全部通過！")
    finally:
        if tmp_db_p.exists():
            tmp_db_p.unlink()

def test_f50_advanced_escalation_and_radar():
    """
    [TCV-F50-006] 進階缺失 ➔ 裁罰演進追蹤與雷達回寫驗證
    """
    main_db = base_dir / "db" / "fsc.db"
    if not main_db.exists():
        return
        
    esc_res = track_deficiency_to_sanction_escalation(main_db, "信用卡")
    assert esc_res["keyword"] == "信用卡"
    assert esc_res["sanctions_found"] >= 1, "[TCV-F50-006] 演進追蹤未命中處分書"
    
    radar_res = sync_sanctions_to_supervisory_radar(main_db)
    assert radar_res["status"] == "SUCCESS", "[TCV-F50-006] 雷達回寫失敗"
    assert radar_res["radar_records_updated"] >= 50
    
    print("✅ F50 進階 [TCV-F50-006] 測試通過！")

if __name__ == "__main__":
    test_f50_full_lifecycle()
    test_f50_advanced_escalation_and_radar()
