# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 將模組與 src 路徑加入 sys.path
module_dir = Path(__file__).resolve().parent.parent
base_dir = module_dir.parent.parent
src_dir = base_dir / "src"
sys.path.insert(0, str(module_dir))
sys.path.insert(0, str(src_dir))

from a00_core.utils.date_parser import parse_taiwan_date_universal
from a00_core.utils.cleaners import safe_float, safe_int, clean_text
from a00_core.utils.identity_resolver import validate_tax_id
from a00_core.metadata_manager import register_submodule_metadata, get_all_registered_modules
from etl import build_f00_master_index
from commands_f00 import search_global_entities, query_entity_360, query_entity_relations

def test_f00_utils():
    """測試 F00 通用 Library"""
    # 1. 日期轉換
    assert parse_taiwan_date_universal("090/11/28") == "2001-11-28"
    assert parse_taiwan_date_universal("115.08.19") == "2026-08-19"
    assert parse_taiwan_date_universal("0771012") == "1988-10-12"
    assert parse_taiwan_date_universal("11507") == "2026-07"
    assert parse_taiwan_date_universal("2026-09-05") == "2026-09-05"
    
    # 2. 數值清洗
    assert safe_float("1,234.56") == 1234.56
    assert safe_float("-113,394") == -113394.0
    assert safe_float("15.2%") == 15.2
    assert safe_float("-") == 0.0
    assert safe_int("9,876") == 9876
    assert clean_text(" 國泰   世華  ") == "國泰 世華"
    
    # 3. 統編檢核 (台積電 22099131, 鴻海 04541302)
    assert validate_tax_id("22099131") is True
    assert validate_tax_id("04541302") is True
    assert validate_tax_id("12345678") is False
    print("✅ 通用 Library 單元測試 100% 通過！")

def test_f00_isolated_hub():
    """測試 F00 Master Hub 在臨時隔離 DB 中的全域生命週期與 360 度實體註冊"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_p = Path(tmp_db.name)
        
    try:
        # 建立模擬 F10 金控與銀行表
        conn = sqlite3.connect(str(tmp_db_p))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE f10_financial_holdings (
                holding_name TEXT PRIMARY KEY,
                group_assets_billion REAL,
                group_net_worth_billion REAL,
                subsidiaries_text TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO f10_financial_holdings VALUES ('國泰金控', 14991.0, 1130.0, '國泰世華商業銀行, 國泰人壽')
        """)
        cursor.execute("""
            CREATE TABLE f10_bank_asset_quality (
                bank_name TEXT PRIMARY KEY,
                loan_total REAL,
                npl_ratio REAL,
                coverage_ratio REAL
            )
        """)
        cursor.execute("""
            INSERT INTO f10_bank_asset_quality VALUES ('國泰世華商業銀行', 2000000.0, 0.09, 1800.0)
        """)
        cursor.execute("""
            CREATE TABLE f30_insurance_institutions (
                insurer_name TEXT PRIMARY KEY,
                insurer_type TEXT,
                inner_staff_count INTEGER,
                field_agent_count INTEGER,
                underwriting_count INTEGER,
                claim_count INTEGER,
                actuary_count INTEGER
            )
        """)
        cursor.execute("""
            INSERT INTO f30_insurance_institutions VALUES ('國泰人壽保險股份有限公司', 'LIFE', 4000, 20000, 200, 250, 10)
        """)
        conn.commit()
        conn.close()
        
        # 執行 F00 ETL (實體註冊 + 關係拓樸 + FTS5 倒排)
        res = build_f00_master_index(tmp_db_p)
        assert res["status"] == "SUCCESS"
        assert res["total_entities_registered"] == 3
        assert res["total_entities_indexed"] == 3
        assert res["total_relations_built"] == 2
        
        # 測試 FTS5 全域檢索
        search_res = search_global_entities(tmp_db_p, "國泰")
        assert len(search_res) >= 1
        assert "國泰" in search_res[0]["primary_name"]
        
        # 測試 360 度全景實體檔案查詢
        profile_fhc = query_entity_360(tmp_db_p, "國泰金控")
        assert profile_fhc is not None
        assert profile_fhc["fhc_assets_billion"] == 14991.0
        assert profile_fhc["entity_class"] == "FHC"
        
        # 測試元資料註冊
        modules = get_all_registered_modules(tmp_db_p)
        assert len(modules) >= 2
        assert any(m["table_name"] == "f00_entity_registry" for m in modules)
        assert any(m["table_name"] == "fts_fsc_global" for m in modules)
        assert any(m["table_name"] == "f00_entity_relations" for m in modules)
        
        # 測試集團控制力拓樸關聯查詢
        rel_fhc = query_entity_relations(tmp_db_p, "國泰金控")
        assert rel_fhc["entity"] is not None
        assert len(rel_fhc["subsidiaries"]) >= 1
        assert any("國泰世華" in s["related_name"] for s in rel_fhc["subsidiaries"])
        
        # 測試反向查詢 (銀行被金控控制)
        rel_bank = query_entity_relations(tmp_db_p, "國泰世華商業銀行")
        assert rel_bank["entity"] is not None
        assert len(rel_bank["parents_or_shareholders"]) >= 1
        assert any("國泰金控" in p["related_name"] for p in rel_bank["parents_or_shareholders"])

        print("✅ F00 Master Hub 隔離單元測試與 360 度實體註冊、控制力拓樸網路 100% 通過！")
    finally:
        if tmp_db_p.exists():
            tmp_db_p.unlink()


def test_f00_global_fts_all_domains():
    """驗證母大腦主庫中是否完整涵蓋五大業務域之 FTS5 倒排索引"""
    main_db = base_dir / "db" / "fsc.db"
    if not main_db.exists():
        return
        
    # 驗證 F40 缺失命中
    res_f40 = search_global_entities(main_db, "創投", limit=5)
    assert len(res_f40) >= 1, "全域倒排未命中 F40 金檢缺失"
    
    # 驗證 F50 處分書命中
    res_f50 = search_global_entities(main_db, "信用卡疑義帳款", limit=5)
    assert len(res_f50) >= 1, "全域倒排未命中 F50 處分書"
    
    # 驗證 360 profile 包含爭議申訴指標
    prof = query_entity_360(main_db, "中國信託商業銀行")
    assert prof is not None
    assert prof.get("ombudsman_complaint_count") is not None
    assert prof["ombudsman_complaint_count"] > 0
    
    # 驗證 F60 VASP 與金融科技沙盒命中
    res_f60_vasp = search_global_entities(main_db, "幣託", limit=5)
    assert len(res_f60_vasp) >= 1, "全域倒排未命中 F60 VASP 實體"
    res_f60_sb = search_global_entities(main_db, "好好投資", limit=5)
    assert len(res_f60_sb) >= 1, "全域倒排未命中 F60 沙盒實體"

    # 驗證 360 profile 整合 F60 VASP 與沙盒欄位
    prof_vasp = query_entity_360(main_db, "現代財富科技")
    assert prof_vasp is not None
    assert prof_vasp.get("vasp_id") == "VASP-001"
    assert prof_vasp.get("vasp_compliance_status") == "COMPLIANT"

    prof_sb = query_entity_360(main_db, "好好投資")
    assert prof_sb is not None
    assert prof_sb.get("sandbox_case_no") == "FS-2020-001"
    assert prof_sb.get("sandbox_status") == "GRADUATED"
    
    print("✅ F00 Master Hub 全域六域倒排與 360° 虛實跨界串接測試通過！")

if __name__ == "__main__":
    test_f00_utils()
    test_f00_isolated_hub()
    test_f00_global_fts_all_domains()
