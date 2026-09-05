# -*- coding: utf-8 -*-
"""
F30 單元測試腳本：涵蓋 F30_TEST_PLAN.md 中 [TCV-F30-001] ~ [TCV-F30-006]
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 將模組路徑與 src 加入 sys.path
module_dir = Path(__file__).resolve().parent.parent
src_dir = module_dir.parent.parent / "src"
sys.path.insert(0, str(module_dir))
sys.path.insert(0, str(src_dir))

from etl import run_f30_etl
from commands_f30 import (
    query_insurance_institutions,
    query_complaint_trends,
    query_compensation_fund,
    query_holding_insurer_summary
)

def test_f30_full_lifecycle():
    """在隔離臨時資料庫中執行 F30 測試案例驗證"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_p = Path(tmp_db.name)
        
    try:
        # [TCV-F30-001] 自包含隔離建表與 ETL
        res = run_f30_etl(db_path=tmp_db_p)
        assert res["status"] == "SUCCESS", "[TCV-F30-001] ETL 執行失敗"
        assert res["insurers_loaded"] >= 50, "[TCV-F30-001] 保險機構未達 50 家"
        assert res["complaints_loaded"] >= 20, "[TCV-F30-001] 申訴歷史紀錄未達 20 筆"
        assert res["fund_loaded"] >= 20, "[TCV-F30-001] 特別補償基金未達 20 筆"
        
        conn = sqlite3.connect(str(tmp_db_p))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # [TCV-F30-002] 驗證保險機構與精算人力資料結構
        cursor.execute("SELECT * FROM f30_insurance_institutions WHERE insurer_name LIKE '%國泰人壽%'")
        cathay = cursor.fetchone()
        assert cathay is not None, "[TCV-F30-002] 找不到國泰人壽"
        assert cathay["insurer_type"] == "LIFE"
        assert cathay["inner_staff_count"] > 0
        assert cathay["actuary_count"] > 0
        
        # [TCV-F30-003] 驗證產險機構分類
        cursor.execute("SELECT * FROM f30_insurance_institutions WHERE insurer_name LIKE '%富邦產物%'")
        fubon_p = cursor.fetchone()
        assert fubon_p is not None, "[TCV-F30-003] 找不到富邦產物"
        assert fubon_p["insurer_type"] == "PROPERTY"
        
        # [TCV-F30-004] 驗證爭議申訴趨勢資料型別與非負約束
        cursor.execute("SELECT * FROM f30_insurance_complaint_trends ORDER BY eval_year DESC LIMIT 1")
        comp = cursor.fetchone()
        assert comp is not None, "[TCV-F30-004] 申訴表為空"
        assert comp["complaint_count"] >= 0
        assert comp["complaint_ratio"] >= 0.0
        
        # [TCV-F30-005] 驗證特別補償基金每件平均計算
        cursor.execute("SELECT * FROM f30_special_compensation_fund WHERE compensated_cases > 0 LIMIT 1")
        fund = cursor.fetchone()
        assert fund is not None, "[TCV-F30-005] 特別補償基金表為空"
        assert fund["avg_compensation_thousand"] > 0.0
        
        conn.close()
        
        # [TCV-F30-006] 驗證查詢命令 API
        ins_list = query_insurance_institutions(tmp_db_p, limit=5, order_by="actuary_count")
        assert len(ins_list) == 5
        assert ins_list[0]["actuary_count"] >= ins_list[1]["actuary_count"]
        
        trends = query_complaint_trends(tmp_db_p, limit=5)
        assert len(trends) == 5
        
        funds = query_compensation_fund(tmp_db_p, limit=5)
        assert len(funds) == 5
        
    finally:
        if tmp_db_p.exists():
            tmp_db_p.unlink()
