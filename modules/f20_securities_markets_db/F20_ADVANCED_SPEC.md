# 🚀 F20: 高級延伸功能與跨模組協作規格書 (F20_ADVANCED_SPEC.md)

* **模組代號**：`f20_securities_markets_db`
* **版本號**：`v1.0.0` (跨模組穿透與資本市場監理架構)

---

## 1. 跨模組業務穿透協作規格 (Cross-Module Synergies)

* **`[F20-ADV-001]` F20 ↔ F10 (金控/銀行) 上市金融股營收與資產品質評價偏離分析 (Equity-Credit Misalignment)**
  * **聯動對象**：`modules/f10_banking_credit_db` (`f10_financial_holdings`, `f10_bank_asset_quality`)。
  * **協作情境**：
    - 將 14 家上市櫃金控之股票代號（如 2881 富邦金、2882 國泰金）與銀行局資產品質進行主鍵穿透。
    - 檢驗「商業銀行逾放比下降、獲利創高，但上市金控股價淨值比 (P/B) 卻嚴重低估」之市場定價偏離訊號。
  * **跨模組 View (`v_f20_f10_financial_group_synergy`)**：
    ```sql
    CREATE VIEW IF NOT EXISTS v_f20_f10_financial_group_synergy AS
    SELECT 
        c.company_code,
        c.company_name,
        h.holding_name,
        h.group_assets_billion,
        r.revenue_year_month,
        r.current_month_revenue,
        r.yoy_growth_rate
    FROM f20_companies c
    JOIN f10_financial_holdings h ON h.holding_name LIKE '%' || c.company_name || '%'
    LEFT JOIN f20_monthly_revenues r ON c.company_code = r.company_code;
    ```

* **`[F20-ADV-002]` F20 ↔ F40 (金融檢查) 董監大股東異常與金檢主要缺失聯合勾稽 (Governance Deficiencies Trace)**
  * **聯動對象**：`modules/f40_financial_inspection_db` (`f40_exam_deficiencies_fhc`)。
  * **協作情境**：
    - 透過 `f20_major_shareholders` 大股東持股結構，勾稽檢查局「金控公司主要金檢缺失」。
    - 針對大股東持股質押比率過高、或外部法人持股過度集中的上市公司，檢視其金檢報告中是否存在「內控遵循缺失」或「關係人關係未依規定揭露」。

* **`[F20-ADV-003]` F20 ↔ F50 (裁罰消保) 重大裁罰對上市櫃股價與營收衝擊回測 (Sanction Impact Backtesting)**
  * **聯動對象**：`modules/f50_sanctions_consumer_db` (`f50_sanctions_rss`)。
  * **協作情境**：
    - 當金管會裁罰上市櫃公司或其子公司時，自動以處分發布日為基準點，回測其當月營收動能 (YoY) 與大股東股權變動情況。

* **`[F20-ADV-004]` F20 ↔ F60 (永續金融) 綠色營收動能與溫室氣體減碳路徑對齊 (Green Revenue & ESG Alignment)**
  * **聯動對象**：`modules/f60_fintech_esg_db` (`f60_greenhouse_gas_report`)。
  * **協作情境**：
    - 比對高碳排產業（如鋼鐵、水泥、半導體）上市公司營收成長與年度範疇一、範疇二溫室氣體排放量，計算「每千元營收之碳排密集度 (Carbon Intensity)」。

---

## 2. 前瞻協作與未來專案規格 ([FUTURE] Scope)

* **`[F20-FUT-001]` 櫃買 TPEX 本益比殖利率與集中市場自動套利估值模型 [FUTURE]**
  * **狀態**：`PROPOSED / FUTURE` (預期於 `f20_market_valuation_sample.csv` 全量導入時啟動)。
  * **預期目標**：自動運算上櫃與上市公司之產業平均本益比、殖利率，為投資人與研究員提供跨市場估值比較。

* **`[F20-FUT-002]` 期貨與衍生性商品期現貨避險跨市場監控 (Futures-Cash Hedging Monitor) [FUTURE]**
  * **狀態**：`PROPOSED / FUTURE` (預期於 `f20_futures_volume_sample.csv` 期交所資料入庫時啟用)。
  * **預期目標**：監控台指期貨大型期貨商造市量與上市現貨交易量之比率，偵測市場流動性驟降之閃崩預警。
