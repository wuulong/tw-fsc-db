# F30: 保險市場與精算風險智庫 - 測試計畫 (F30_TEST_PLAN.md)

## 1. 測試目標
驗證 F30 模組自包含生命週期、SQLite 原生 UDF 註冊、三實體表與分析檢視之正確性，以及與主庫之整合相容性。

## 2. 測試範圍
1. **獨立生命週期隔離測試 (Isolated Lifecycle Test)**：
   - 建立暫時性隔離資料庫（`:memory:` 或 `temp_f30_test.db`）。
   - 載入 `schema.sql`，確認三實體表與檢視均成功建立。
2. **UDF 函數註冊與精確計算測試 (UDF Calculation Test)**：
   - 測試 `calc_avg_compensation_ntd(expense, count)` 之邊界條件（零件數、負數、Null）。
3. **ETL 地面真值匯入測試 (ETL Data Import Test)**：
   - 執行 `run_f30_etl`，驗證 52 家產壽險機構、26 筆歷史申訴紀錄、28 筆特別補償基金運作資料均精確寫入。
4. **業務指標與檢視查詢測試 (Views & Analytics Test)**：
   - 查詢 `v_f30_special_compensation_fund_metrics`，驗證每案平均給付金額之正確性。
   - 查詢 `v_f30_insurer_staff_summary`，驗證產險 vs 壽險之人力配置分組統計。
5. **API 查詢命令測試 (Query API Test)**：
   - 驗證 `query_insurance_institutions`、`query_complaint_trends`、`query_compensation_fund` 之返回格式與排序正確性。
