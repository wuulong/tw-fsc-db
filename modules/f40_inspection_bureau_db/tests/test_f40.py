# -*- coding: utf-8 -*-
"""
F40 單元測試腳本：涵蓋 F40_TEST_PLAN.md 中 [TCV-F40-001] ~ [TCV-F40-007]
包含基礎自包含 ETL、FTS5 全文檢索、高頻分析，以及進階跨模組集團拓樸穿透與監理雷達計分連動。
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

from etl import run_f40_etl
from commands_f40 import (
    search_exam_deficiencies,
    query_deficiency_categories,
    query_inspection_executions,
    query_holding_deficiency_penetration,
    sync_deficiency_supervisory_radar
)

def test_f40_full_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_p = Path(tmp_db.name)
        
    try:
        # [TCV-F40-001] 自包含隔離建表與 ETL
        res = run_f40_etl(db_path=tmp_db_p)
        assert res["status"] == "SUCCESS", "[TCV-F40-001] ETL 執行失敗"
        assert res["deficiencies_loaded"] >= 90, "[TCV-F40-001] 缺失筆數未達 90"
        assert res["executions_loaded"] >= 40, "[TCV-F40-001] 檢查執行未達 40"
        
        # [TCV-F40-002] FTS5 全文檢索
        search_res = search_exam_deficiencies(tmp_db_p, "創投")
        assert len(search_res) >= 1, "[TCV-F40-002] FTS5 檢索 '創投' 無結果"
        assert any("創投" in r["deficiency_detail"] or "創投" in r["improvement_action"] for r in search_res)
        
        # [TCV-F40-003] 高頻缺失分析檢視
        cats = query_deficiency_categories(tmp_db_p, target_sector="HOLDING")
        assert len(cats) >= 5, "[TCV-F40-003] 金控缺失分類不足 5 項"
        assert cats[0]["deficiency_count"] >= cats[1]["deficiency_count"]
        
        # [TCV-F40-004] 檢查執行統計
        execs = query_inspection_executions(tmp_db_p, limit=5)
        assert len(execs) == 5, "[TCV-F40-004] 檢查執行筆數不符"
        assert execs[0]["inspected_count"] > 0
        
        # [TCV-F40-005] 容錯測試
        empty_res = search_exam_deficiencies(tmp_db_p, "")
        assert empty_res == []
        
        print("✅ F40 基礎 5 大測試案例全部通過！")
    finally:
        if tmp_db_p.exists():
            tmp_db_p.unlink()

def test_f40_advanced_penetration_and_radar():
    """
    驗證 F40 進階功能：
    [TCV-F40-006] 缺失態樣穿透集團股權拓樸 (Deficiency-to-Conglomerate Penetration)
    [TCV-F40-007] 重大缺失計分下沉至 F00 監理綜合風險雷達
    """
    main_db = base_dir / "db" / "fsc.db"
    if not main_db.exists():
        print("⚠️ 主資料庫不存在，跳過跨模組整合測試")
        return
        
    # [TCV-F40-006] 集團股權拓樸穿透
    pen_res = query_holding_deficiency_penetration(main_db, "華南金")
    assert pen_res["holding_name"] == "華南金", "[TCV-F40-006] 穿透金控名稱不符"
    assert pen_res["subsidiaries_count"] >= 5, "[TCV-F40-006] 華南金旗下子公司穿透數不足 5 家"
    assert pen_res["deficiencies_count"] >= 5, "[TCV-F40-006] 金控子公司相關重大缺失不足 5 筆"
    
    # 驗證穿透子公司帶有業務模組指標
    sub_names = [s["canonical_name"] for s in pen_res["penetrated_subsidiaries"]]
    assert "華南商業銀行" in sub_names, "[TCV-F40-006] 未成功穿透出華南商業銀行"
    assert "華南產物保險股份有限公司" in sub_names, "[TCV-F40-006] 未成功穿透出華南產物保險"
    
    # [TCV-F40-007] 監理雷達計分連動
    radar_res = sync_deficiency_supervisory_radar(main_db)
    assert radar_res["status"] == "SUCCESS", "[TCV-F40-007] 雷達同步失敗"
    assert radar_res["radar_records_updated"] >= 40, "[TCV-F40-007] 雷達記錄更新筆數未達 40"
    
    # 驗證 f00_supervisory_radar 內之 exam_deficiency_count 與燈號有效性
    conn = sqlite3.connect(str(main_db))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM f00_supervisory_radar WHERE exam_deficiency_count > 0")
    cnt = c.fetchone()[0]
    assert cnt >= 40, "[TCV-F40-007] 雷達表未正確記錄檢查缺失計分"
    
    c.execute("SELECT composite_risk_level, COUNT(*) FROM f00_supervisory_radar GROUP BY composite_risk_level")
    levels = dict(c.fetchall())
    assert "YELLOW" in levels or "GREEN" in levels, "[TCV-F40-007] 風險燈號未生成"
    conn.close()
    
    print("✅ F40 進階 [TCV-F40-006] 與 [TCV-F40-007] 測試通過！")

if __name__ == "__main__":
    test_f40_full_lifecycle()
    test_f40_advanced_penetration_and_radar()
