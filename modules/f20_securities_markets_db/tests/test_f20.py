# -*- coding: utf-8 -*-
"""
F20 單元測試腳本：100% 涵蓋 F20_TEST_PLAN.md 中 [TCV-F20-001] ~ [TCV-F20-008]
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

from etl import run_f20_etl
from commands_f20 import query_top_revenue_companies, query_company_profile, query_major_shareholders, query_market_valuations, query_futures_trading

def test_f20_full_lifecycle():
    """在隔離臨時資料庫中執行 8 大測試案例完整驗證"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_p = Path(tmp_db.name)
        
    try:
        # [TCV-F20-008] 自包含隔離建表與 ETL
        res = run_f20_etl(db_path=tmp_db_p)
        assert res["status"] == "SUCCESS", "[TCV-F20-008] ETL 執行狀態失敗"
        assert res["companies_loaded"] > 0, "[TCV-F20-001] ISIN 公司未成功載入"
        assert res["revenues_loaded"] > 0, "[TCV-F20-002] 月營收未成功載入"
        assert res["shareholders_loaded"] > 0, "[TCV-F20-004] 大股東未成功載入"
        
        conn = sqlite3.connect(str(tmp_db_p))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # [TCV-F20-001] 驗證普通股股票與 ISIN
        cursor.execute("SELECT * FROM f20_companies WHERE company_code = '1101'")
        t1101 = cursor.fetchone()
        assert t1101 is not None, "[TCV-F20-001] 找不到台泥 1101"
        assert t1101["company_name"] == "台泥"
        assert t1101["isin_code"] == "TW0001101004"
        assert t1101["listing_date"] == "1962-02-09"
        assert t1101["market_type"] == "上市"
        assert t1101["industry_category"] == "水泥工業"
        
        # [TCV-F20-002] 驗證月營收日期格式與千分位轉型
        cursor.execute("SELECT * FROM f20_monthly_revenues WHERE company_code = '000104'")
        r104 = cursor.fetchone()
        assert r104 is not None, "[TCV-F20-002] 找不到臺銀證券營收"
        assert r104["revenue_year_month"] == "2026-07"
        assert r104["report_date"] == "2026-08-17"
        assert r104["current_month_revenue"] == 156900.0
        
        # [TCV-F20-003] 負營收極值容錯運算 (亞東證券 000218)
        cursor.execute("SELECT * FROM f20_monthly_revenues WHERE company_code = '000218'")
        r218 = cursor.fetchone()
        assert r218 is not None, "[TCV-F20-003] 找不到亞東證券營收"
        assert r218["current_month_revenue"] == -113394.0, "[TCV-F20-003] 負營收被誤轉或歸零"
        assert r218["mom_growth_rate"] < 0, "[TCV-F20-003] 月增率符號異常"
        
        # [TCV-F20-004] 大股東法人特徵解析與確定性雜湊
        cursor.execute("SELECT * FROM f20_major_shareholders WHERE company_code = '1104'")
        sh_rows = cursor.fetchall()
        assert len(sh_rows) >= 3, "[TCV-F20-004] 環泥大股東筆數不足"
        sh_map = {r["shareholder_name"]: r for r in sh_rows}
        assert "宇聲投資股份有限公司" in sh_map
        assert sh_map["宇聲投資股份有限公司"]["is_corporate"] == 1, "[TCV-F20-004] 法人未正確識別"
        assert "侯博義" in sh_map
        assert sh_map["侯博義"]["is_corporate"] == 0, "[TCV-F20-004] 自然人未正確識別"
        assert sh_map["侯博義"]["shareholder_uid"].startswith("SH_1104_")
        
        # [TCV-F20-005] 跨表整合檢視表 v_f20_company_revenue_profile
        prof = query_company_profile(tmp_db_p, "1104")
        assert prof is not None, "[TCV-F20-005] profile 檢視表查詢失敗"
        assert prof["company_name"] == "環泥"
        assert prof["major_shareholders_count"] >= 3
        
        # [TCV-F20-006] F20 ↔ F10 跨模組集團連動 (注入模擬 F10 金控驗證)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS f10_financial_holdings (
                holding_name TEXT PRIMARY KEY,
                group_assets_billion REAL,
                subsidiaries_text TEXT
            )
        """)
        cursor.execute("INSERT INTO f10_financial_holdings VALUES ('富邦金融控股公司', 12000.0, '台北富邦商業銀行、富邦產險、富邦金')")
        cursor.execute("SELECT * FROM v_f20_f10_financial_group_synergy WHERE company_name = '富邦金'")
        syn_row = cursor.fetchone()
        assert syn_row is not None, "[TCV-F20-006] 跨模組集團連動檢視失敗"
        assert syn_row["holding_name"] == "富邦金融控股公司"
        
        # [TCV-F20-007] 全域元資料登記
        cursor.execute("SELECT table_name, record_count FROM sys_module_metadata WHERE module_id = 'f20_securities_markets_db'")
        meta_rows = {r[0]: r[1] for r in cursor.fetchall()}
        assert "f20_companies" in meta_rows
        assert "f20_monthly_revenues" in meta_rows
        assert "f20_major_shareholders" in meta_rows
        assert meta_rows["f20_companies"] > 0
        
        conn.close()
        
        # [TCV-F20-009] 驗證上櫃股票市場估值 (本益比 P/E、殖利率)
        val_list = query_market_valuations(tmp_db_p, limit=5)
        assert len(val_list) > 0, "[TCV-F20-009] 查無市場估值資料"
        assert val_list[0]["dividend_yield"] > 0.0, "[TCV-F20-009] 殖利率未正確計算"

        # [TCV-F20-010] 驗證期交所商品交易量與未平倉
        fut_list = query_futures_trading(tmp_db_p, limit=5)
        assert len(fut_list) > 0, "[TCV-F20-010] 查無期貨交易量資料"
        assert fut_list[0]["total_volume"] > 0, "[TCV-F20-010] 期貨合約成交量為 0"

        print("✅ [TCV-F20-001] ~ [TCV-F20-010] 10 大測試案例 100% 全部通過！")
    finally:
        if tmp_db_p.exists():
            tmp_db_p.unlink()

if __name__ == "__main__":
    test_f20_full_lifecycle()
