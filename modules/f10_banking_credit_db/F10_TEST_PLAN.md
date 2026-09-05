# 🧪 F10: 測試計畫與驗證規範 (F10_TEST_PLAN.md)

本檔案涵蓋 `F10_SPECIFICATION.md` 與 `F10_ADVANCED_SPEC.md` 中所有基本功能與跨部會延伸需求的測試驗證規範。測試腳本位於 `tests/test_f10.py`，驗證門檻要求 100% PASS。

---

## 1. 測試案例矩陣 (Test Cases Matrix)

| 測試案例 ID | 測試目標與涵蓋規格 | 測試輸入與操作 | 預期 PASS 條件 |
| :--- | :--- | :--- | :--- |
| **`[TCV-F10-001]`** | **金控設立表入庫與子公司拆分**<br>`[追溯：FSC-SPC-002, F10-SPEC-2.1]` | 解析 `f10_fhc_setup_sample.csv` 入庫至 `f10_financial_holdings` | 1. 成功載入 14 家金控公司。<br>2. 國泰金控、富邦金控之資產數值大於 0。<br>3. 子公司字串頓號清洗正確，UDF `COUNT_DELIMITED` 精確計算數量。 |
| **`[TCV-F10-002]`** | **本國銀行資產品質清洗入庫**<br>`[追溯：FSC-SPC-002, F10-SPEC-2.2]` | 解析 `f10_banking12_sample.csv` 入庫至 `f10_bank_asset_quality` | 1. 成功載入銀行資料。<br>2. 存款、放款、逾放比與備抵呆帳涵蓋率由 UDF `PARSE_NUM` 轉換為標準浮點數。<br>3. 支援依照逾放比或放款總額排序查詢。 |
| **`[TCV-F10-003]`** | **土地擔保放款餘額與集中度清洗**<br>`[追溯：FSC-SPC-002, F10-SPEC-2.3]` | 解析 `f10_land_loan_sample.csv` 入庫至 `f10_land_collateral_loans` | 1. 成功解析土地放款餘額。<br>2. UDF `BANK_72_2_RATIO` 正確計算土地放款佔比 `land_loan_ratio`。<br>3. 臺灣土地銀行之土地放款金額居首。 |
| **`[TCV-F10-004]`** | **信用卡營運與活卡率指標入庫**<br>`[追溯：F10-SPEC-2.4]` | 解析 `f10_credit_card_sample.csv` 入庫至 `f10_credit_card_operations` | 1. 成功載入 19 家發卡機構。<br>2. 流通卡數、有效卡數、簽帳金額正確入庫。<br>3. UDF `BANK_72_2_RATIO` 計算 `active_card_ratio` (活卡率) > 0%。 |
| **`[TCV-F10-005]`** | **聯徵中心全台企業總貸款趨勢入庫**<br>`[追溯：F10-SPEC-2.5]` | 解析 `f10_corporate_loan_sample.csv` 入庫至 `f10_corporate_loan_trends` | 1. 成功載入月度企貸資料，ISO 年月主鍵 `year_month` (如 2012-05)。<br>2. 自動換算為十億元單位 `loan_total_billion`。<br>3. 支援依照時間倒序檢視信用擴張或緊縮趨勢。 |
| **`[TCV-F10-006]`** | **銀行信用風險監理綜合雷達與 UDF 燈號**<br>`[追溯：F10-SPEC-2.6]` | 查詢檢視表 `v_f10_bank_credit_risk_profile` | 1. 橫向聚合資產品質、土地融資比率與信用卡逾期款。<br>2. UDF `RISK_BADGE` 動態評定風險燈號 (`GREEN`/`YELLOW`/`RED`)。<br>3. 排序與預警指標完全精確。 |
| **`[TCV-F10-007]`** | **跨表金控與旗下銀行總覽檢視**<br>`[追溯：F10-SPEC-2.6]` | 查詢檢視表 `v_f10_holding_banking_summary` | 1. 正確關聯金控、旗下銀行、土地放款比率與信用卡月簽帳額。<br>2. 集團綜效與消費金融滲透率清晰可查。 |
| **`[TCV-F10-008]`** | **五大資料表元資料集中註冊**<br>`[追溯：FSC-SPC-008, F00-SPEC-2.1]` | 執行 F10 ETL 入庫流程 | 1. 自動於 `sys_module_metadata` 登記 5 大實體表名稱。<br>2. 登記正確記錄筆數與時間戳。 |
| **`[TCV-F10-009]`** | **臨時隔離 DB 自包含黃金生命週期**<br>`[追溯：Submodule Golden Cycle]` | 在完全獨立的臨時 SQLite DB 執行建表、ETL 與查詢 | 完全不依賴母資料庫既有資料，100% 獨立運行通過。 |

---

## 2. 自動化驗證執行方式

```bash
# 執行 F10 子模組單元測試
/Users/wuulong/opt/anaconda3/envs/m2504/bin/python events-2026Q3/fsc-db-in/tw-fsc-db/modules/f10_banking_credit_db/tests/test_f10.py
```