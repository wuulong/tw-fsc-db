# -*- coding: utf-8 -*-
"""
F60 金融科技、虛擬資產平台 (VASP) 與永續金融智庫單元測試
對齊 F60_TEST_PLAN.md: [TCV-F60-001] ~ [TCV-F60-006]
"""

import sys
import tempfile
import unittest
from pathlib import Path

# 引用路徑
module_dir = Path(__file__).resolve().parent.parent
src_dir = module_dir.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(module_dir) not in sys.path:
    sys.path.insert(0, str(module_dir))

from etl import run_f60_etl
from commands_f60 import (
    query_vasp_registry,
    query_fintech_sandbox,
    query_greenhouse_gas_trends,
    penetrate_sandbox_partner_institution,
    query_vasp_aml_sanctions_synergy
)
from a00_core.udfs import get_connection_with_udfs

class TestF60FintechVaspDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db = Path(cls.temp_dir.name) / "test_f60.db"
        
        # 建立 F10 與 F50 模擬綱要以供穿透測試
        conn = get_connection_with_udfs(cls.test_db)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS f10_bank_asset_quality (
                bank_name TEXT PRIMARY KEY,
                deposit_amount REAL,
                pretax_profit REAL,
                loan_total REAL,
                overdue_loan_total REAL,
                allowance_bad_debt REAL,
                net_worth REAL,
                npl_ratio REAL,
                coverage_ratio REAL,
                updated_at TEXT NOT NULL
            );
        """)
        cur.execute("""
            INSERT INTO f10_bank_asset_quality (
                bank_name, deposit_amount, pretax_profit, loan_total, overdue_loan_total,
                allowance_bad_debt, net_worth, npl_ratio, coverage_ratio, updated_at
            ) VALUES ('台北富邦商業銀行', 3150000, 28000, 2200000, 2640, 15840, 250000, 0.12, 600.0, '2026-09-05T00:00:00');
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS f50_sanctions (
                sanction_uid TEXT PRIMARY KEY,
                doc_no TEXT NOT NULL,
                sanction_date TEXT NOT NULL,
                target_name TEXT NOT NULL,
                tax_id TEXT,
                penalty_fine_ntd REAL DEFAULT 0.0,
                agency_bureau TEXT NOT NULL,
                main_subject TEXT NOT NULL,
                violation_facts TEXT,
                legal_basis TEXT,
                source_url TEXT,
                updated_at TEXT NOT NULL,
                attributes_json TEXT
            );
        """)
        cur.execute("""
            INSERT INTO f50_sanctions (
                sanction_uid, doc_no, sanction_date, target_name, penalty_fine_ntd,
                agency_bureau, main_subject, violation_facts, legal_basis, updated_at
            ) VALUES (
                'SNC-001', '金管銀控字第10902741971號', '2020-12-29', '花旗(台灣)商業銀行股份有限公司',
                10000000, '銀行局', '處分新臺幣1,000萬元罰鍰', '貴行未依規定訂定虛擬貨幣交易平台業者相關監控態樣，將平台業者及其使用者一併納入監控態樣進行監控。',
                '銀行法第45條之1', '2026-09-05T00:00:00'
            );
        """)
        conn.commit()
        conn.close()

        # 執行 F60 ETL 匯入
        cls.etl_res = run_f60_etl(cls.test_db)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_tcv_f60_001_etl_import(self):
        """[TCV-F60-001] 隔離環境自包含生命週期與 ETL 匯入驗證"""
        self.assertTrue(self.etl_res["success"])
        self.assertGreaterEqual(self.etl_res["vasp_records"], 4)
        self.assertGreaterEqual(self.etl_res["sandbox_records"], 2)
        self.assertGreaterEqual(self.etl_res["ghg_records"], 35)

    def test_tcv_f60_002_vasp_registry(self):
        """[TCV-F60-002] VASP 洗錢防制合規業者統編與品牌檢驗"""
        vasp_list = query_vasp_registry(self.test_db, limit=10)
        self.assertGreaterEqual(len(vasp_list), 4)
        maicoin = next((v for v in vasp_list if "MaiCoin" in v["brand_name"]), None)
        self.assertIsNotNone(maicoin)
        self.assertEqual(maicoin["tax_id"], "54341909")
        self.assertEqual(maicoin["status"], "COMPLIANT")
        self.assertEqual(maicoin["fiat_custody_bank"], "遠東國際商業銀行")

    def test_tcv_f60_003_fintech_sandbox(self):
        """[TCV-F60-003] 金融科技沙盒案狀態與實驗領域檢驗"""
        sandbox_list = query_fintech_sandbox(self.test_db, limit=10)
        self.assertGreaterEqual(len(sandbox_list), 2)
        howhow = next((s for s in sandbox_list if "好好投資" in s["applicant"]), None)
        self.assertIsNotNone(howhow)
        self.assertEqual(howhow["status"], "GRADUATED")
        self.assertEqual(howhow["partner_institution"], "台北富邦商業銀行")

    def test_tcv_f60_004_greenhouse_gas_trends(self):
        """[TCV-F60-004] 國家溫室氣體歷年時序與淨排碳指標檢驗"""
        ghg_list = query_greenhouse_gas_trends(self.test_db, limit=5)
        self.assertGreaterEqual(len(ghg_list), 5)
        latest = ghg_list[0]
        self.assertEqual(latest["year"], 2024)
        self.assertGreater(latest["net_ghg_emission_value"], 200000)

    def test_tcv_f60_005_sandbox_penetration(self):
        """[TCV-F60-005] 進階穿透：沙盒創新案合作特許銀行體質穿透驗證 ([F60-ADV-FSC-001])"""
        penetration = penetrate_sandbox_partner_institution(self.test_db, "好好投資")
        self.assertIsNotNone(penetration)
        self.assertIsNotNone(penetration["partner_bank_asset_quality"])
        self.assertEqual(penetration["partner_bank_asset_quality"]["bank_name"], "台北富邦商業銀行")
        self.assertEqual(penetration["partner_bank_asset_quality"]["npl_ratio"], 0.12)

    def test_tcv_f60_006_vasp_aml_sanctions(self):
        """[TCV-F60-006] 進階穿透：虛擬通貨洗防裁罰關聯驗證 ([F60-ADV-FSC-002])"""
        sanctions = query_vasp_aml_sanctions_synergy(self.test_db, "虛擬貨幣")
        self.assertGreaterEqual(len(sanctions), 1)
        citi_sanction = sanctions[0]
        self.assertIn("花旗", citi_sanction["target_name"])
        self.assertEqual(citi_sanction["penalty_fine_ntd"], 10000000)

if __name__ == "__main__":
    unittest.main()
