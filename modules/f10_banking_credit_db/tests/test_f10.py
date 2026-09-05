# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 將模組路徑與 src 加入 sys.path
module_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(module_dir))
src_dir = module_dir.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from etl import run_f10_etl
from commands_f10 import (
    query_financial_holdings,
    query_bank_asset_quality,
    query_land_collateral_loans,
    query_credit_card_operations,
    query_corporate_loan_trends,
    query_bank_credit_risk_radar,
    query_holding_banking_summary
)

def test_f10_isolated_lifecycle():
    """驗證 F10 子模組可以在全新隔離的臨時資料庫中獨立完成 5 大資料集建表、UDF ETL 與查詢"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_path = Path(tmp_db.name)
        
    try:
        # 1. 執行全量 ETL 注入隔離 DB
        res = run_f10_etl(db_path=tmp_db_path)
        assert res["status"] == "SUCCESS"
        assert res["fhc_records_loaded"] > 0
        assert res["banking_records_loaded"] > 0
        assert res["land_loan_records_loaded"] > 0
        assert res["credit_card_records_loaded"] > 0
        assert res["corporate_loan_records_loaded"] > 0
        assert res["total_records"] >= 90
        
        # 2. 測試查詢金控 (f10_financial_holdings)
        fhc_list = query_financial_holdings(tmp_db_path, limit=5)
        assert len(fhc_list) > 0
        assert "holding_name" in fhc_list[0]
        assert fhc_list[0]["group_assets_billion"] > 0
        assert fhc_list[0]["subsidiaries_count"] > 0
        
        # 3. 測試查詢銀行資產品質 (f10_bank_asset_quality)
        bk_list = query_bank_asset_quality(tmp_db_path, limit=5)
        assert len(bk_list) > 0
        assert "bank_name" in bk_list[0]
        assert bk_list[0]["loan_total"] > 0
        
        # 4. 測試查詢土地擔保放款 (f10_land_collateral_loans) & UDF 計算之 land_loan_ratio
        land_list = query_land_collateral_loans(tmp_db_path, limit=5)
        assert len(land_list) > 0
        assert "land_loan_balance" in land_list[0]
        assert land_list[0]["land_loan_ratio"] >= 0.0
        
        # 5. 測試查詢信用卡營運 (f10_credit_card_operations)
        cc_list = query_credit_card_operations(tmp_db_path, limit=5)
        assert len(cc_list) > 0
        assert "cards_effective" in cc_list[0]
        assert cc_list[0]["active_card_ratio"] > 0.0
        
        # 6. 測試查詢企貸趨勢 (f10_corporate_loan_trends)
        corp_list = query_corporate_loan_trends(tmp_db_path, limit=5)
        assert len(corp_list) > 0
        assert "year_month" in corp_list[0]
        assert corp_list[0]["loan_total_billion"] > 0.0
        
        # 7. 測試銀行信用風險綜合監理雷達 (v_f10_bank_credit_risk_profile) & UDF RISK_BADGE
        radar_list = query_bank_credit_risk_radar(tmp_db_path, limit=5)
        assert len(radar_list) > 0
        assert "supervisory_risk_badge" in radar_list[0]
        assert radar_list[0]["supervisory_risk_badge"] in ["GREEN", "YELLOW", "RED"]
        
        # 8. 測試跨表彙整檢視 (v_f10_holding_banking_summary)
        summary_list = query_holding_banking_summary(tmp_db_path, limit=5)
        assert len(summary_list) > 0
        assert "cc_signing_amount" in summary_list[0]
        
        print("✅ F10 子模組五大資料集與 UDF 隔離生命週期測試 100% 通過！")
    finally:
        if tmp_db_path.exists():
            tmp_db_path.unlink()

if __name__ == "__main__":
    test_f10_isolated_lifecycle()