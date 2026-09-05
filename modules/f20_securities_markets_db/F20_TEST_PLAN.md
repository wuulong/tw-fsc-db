# 🧪 F20: 測試計畫與驗證規範 (F20_TEST_PLAN.md)

本檔案涵蓋 `F20_SPECIFICATION.md` 與 `F20_ADVANCED_SPEC.md` 中所有功能與進階需求的測試計畫。測試腳本位於 `tests/test_f20.py`，驗證門檻要求 100% PASS。

---

## 1. 測試案例矩陣 (Test Cases Matrix)

| 測試案例 ID | 測試目標與涵蓋規格 | 測試輸入與操作 | 預期 PASS 條件 |
| :--- | :--- | :--- | :--- |
| **`[TCV-F20-001]`** | **公司基準主表與 ISIN 解析**<br>`[追溯：FSC-SPC-003, F20-ADV-001]` | 解析 `f20_isin_companies_sample.csv` (HTML Table) | 1. 成功提取 4 碼普通股上市公司至 `f20_companies`。<br>2. 排除 ETF/ETN/TDR。<br>3. `isin_code` 為 `TW0001101004`，上市日為 `1962-02-09`。 |
| **`[TCV-F20-002]`** | **月營收日期與數值清洗**<br>`[追溯：FSC-SPC-003, F20-SPEC-2.2]` | 解析 `f20_monthly_revenue_sample.csv` 存入 `f20_monthly_revenues` | 1. 民國年月 `11507` 轉為 `2026-07`。<br>2. 出表日 `1150817` 轉為 `2026-08-17`。<br>3. 當月營收千元轉換為正確浮點數。 |
| **`[TCV-F20-003]`** | **負營收極值容錯運算**<br>`[追溯：F20-ADV-002]` | 解析亞東證券 (`000218`) 當月營收 `-113394` | 1. `current_month_revenue` 精確存入 `-113394.0`，未被歸零。<br>2. 月增率 `-214.95%` 正確解析儲存。 |
| **`[TCV-F20-004]`** | **大股東識別與去重雜湊**<br>`[追溯：FSC-SPC-001, F20-ADV-003]` | 解析 `f20_major_shareholders_sample.csv` 存入 `f20_major_shareholders` | 1. 環泥 (`1104`) 提取出 3 名大股東。<br>2. `宇聲投資` 與 `升元投資` 其 `is_corporate = 1`；`侯博義` 其 `is_corporate = 0`。<br>3. 主鍵包含確定性 MD5 雜湊。 |
| **`[TCV-F20-005]`** | **跨表整合檢視表查詢**<br>`[追溯：F20-SPEC-2.4]` | 查詢檢視表 `v_f20_company_revenue_profile` | 能夠輸出包含公司名、產業別、月營收年增率、大股東人數與摘要清單之聚合結果。 |
| **`[TCV-F20-006]`** | **F20 ↔ F10 跨模組集團連動**<br>`[追溯：F20-ADV-004]` | 驗證跨模組檢視表 `v_f20_f10_financial_group_synergy` | 在含有 F10 金控的環境下，能正確將金控與上市證券進行關聯。 |
| **`[TCV-F20-007]`** | **全域元資料登記與 FTS5 投影**<br>`[追溯：F20-ADV-005, FSC-SPC-008]` | 執行 F20 ETL 與 F00 全域倒排重構 | 1. `sys_module_metadata` 登記 `f20_companies`, `f20_monthly_revenues`, `f20_major_shareholders`。<br>2. `fts_fsc_global` 透過關鍵字檢索「台泥」或「環泥」精準命中。 |
| **`[TCV-F20-008]`** | **臨時隔離 DB 自包含生命週期**<br>`[追溯：Submodule Golden Cycle]` | 在完全獨立的臨時 SQLite DB 執行建表、ETL 與查詢 | 完全不依賴母資料庫既有資料，100% 獨立運行通過。 |

---

## 2. 自動化驗證執行方式

```bash
# 執行 F20 子模組單元測試
python events-2026Q3/fsc-db-in/tw-fsc-db/modules/f20_securities_markets_db/tests/test_f20.py
```
