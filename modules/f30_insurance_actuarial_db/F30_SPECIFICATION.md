# 📋 F30: 保險市場與精算風險模組基礎規格書 (F30_SPECIFICATION.md)

* **模組代號**：`f30_insurance_actuarial_db`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 保險局 / 財團法人金融消費評議中心 / 汽車交通事故特別補償基金
* **版本號**：`v2.0.0` (業務本位粗粒度聚合架構 + 地面真值齊備)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-001]` 權威法人統編主鍵自動繫結規格
  * `[FSC-SPC-004]` 保險業清償能力與消費者權益保護監理規格

---

## 1. 模組定位與業務本位原則 (Module Scope & Business-First Principles)

> 💡 **核心原則**：「功能不足，效能有什麼用！」
> 保險市場是社會安全網的最終防火牆。本模組不只記錄保險公司名稱，而是深度聚焦於**保險公司精算與專業人力結構、全台保險爭議與申訴率趨勢、以及汽車交通事故特別補償基金運作**，落實保險監理 4 大核心情境。

---

## 2. 四大實戰業務情境規格發想 (Four Real-World Business Scenarios)

### 2.1 保險機構權威名冊與精算/核保/理賠專業人力結構
* **業務情境**：
  - 台灣保險市場包含產物保險（15家以上）與人壽保險（20家以上）兩大範疇。
  - 保險公司的核心風控能力取決於「精算人員 (Actuary)」、「核保人員 (Underwriting)」與「理賠人員 (Claim)」之配置規模。
* **資料模型 (`f30_insurance_institutions`)**：
  - 整合 `f31_insurance_hr.json` 全國 52 家產壽險公司之最新專業人力統計。
  - 主鍵為 `insurer_name`，精確記錄內勤人力、外勤人力、精算/核保/理賠專業人數與精算人才集中度比率。

### 2.2 全台保險爭議申訴率與紛爭解決機制趨勢
* **業務情境**：
  - 評議中心每年接獲數千件保戶申訴案件（理賠爭議、招攬糾紛）。
  - 主管機關需要動態監測全台「申訴件數」、「簽單契約件數」以及「依申訴人意見辦理比率」與「和解比率」，掌握消費者權益保護指標。
* **資料模型 (`f30_insurance_complaint_trends`)**：
  - 整合 `f32_insurance_complaints.csv` 歷史跨年度申訴與紛爭處理統計。
  - 包含申訴比率 (%)、申訴案件和解率 (%)、保險公司承保件數規模。

### 2.3 汽車交通事故特別補償基金運行與社會救助
* **業務情境**：
  - 針對肇事逃逸、未投保強制險之受害人，由特別補償基金提供救助。
  - 需掌握每年度「分擔額收入」、「補償支出總額」與「補償受害件數」，評估基金財務平衡與支出壓力。
* **資料模型 (`f30_special_compensation_fund`)**：
  - 整合 `f33_special_compensation_fund.csv` 歷年基金收支與件數。
  - 透過 UDF 計算「平均每件補償金額 (千元)」，揭露社會安全網涵蓋深度。

### 2.4 跨模組集團保險全景與精算風險雷達檢視表
* **業務情境**：
  - 金控集團旗下通常兼具銀行與大型壽險子公司（如國泰人壽、富邦人壽、凱基人壽）。
  - 透過檢視表 `v_f30_holding_insurer_summary`，一鍵串聯金控總資產與旗下壽險機構專業人力規模。

---

## 3. 基礎資料庫模型與 DDL 規格 (`schema.sql`)

```sql
-- 1. 保險機構專業人力結構與精算配置表
CREATE TABLE IF NOT EXISTS f30_insurance_institutions (
    insurer_name TEXT PRIMARY KEY,        -- 保險機構法定全銜
    insurer_type TEXT NOT NULL,           -- LIFE(人壽保險), PROPERTY(產物保險), COOP(合作社)
    inner_staff_count INTEGER,            -- 內勤從業人員數
    field_agent_count INTEGER,            -- 外勤從業人員數
    underwriting_count INTEGER,           -- 核保專業人員數
    claim_count INTEGER,                  -- 理賠專業人員數
    actuary_count INTEGER,                -- 精算專業人員數
    report_date TEXT NOT NULL,            -- 基準統計日期 (ISO: YYYY-MM-DD)
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f30_ins_type ON f30_insurance_institutions(insurer_type);
CREATE INDEX IF NOT EXISTS idx_f30_actuary ON f30_insurance_institutions(actuary_count);

-- 2. 全台保險消費爭議申訴歷史趨勢表
CREATE TABLE IF NOT EXISTS f30_insurance_complaint_trends (
    eval_year TEXT PRIMARY KEY,           -- 統計年度 (ISO: YYYY)
    policy_contract_thousand REAL,        -- 簽單契約件數 (千件)
    complaint_count INTEGER,              -- 申訴總件數
    complaint_ratio REAL,                 -- 申訴比率 (%)
    settlement_count INTEGER,             -- 和解件數
    settlement_ratio REAL,                -- 和解占申訴案件比率 (%)
    complainant_favored_ratio REAL,       -- 依申訴人意見辦理比率 (%)
    updated_at TEXT NOT NULL
);

-- 3. 汽車交通事故特別補償基金運作表
CREATE TABLE IF NOT EXISTS f30_special_compensation_fund (
    stat_year TEXT PRIMARY KEY,           -- 統計年度 (ISO: YYYY)
    contribution_income_thousand REAL,    -- 分擔額收入 (千元)
    compensation_expense_thousand REAL,   -- 補償支出 (千元)
    compensated_cases INTEGER,            -- 補償件數
    avg_compensation_thousand REAL,       -- 平均每件補償金額 (千元) (UDF 計算)
    updated_at TEXT NOT NULL
);

-- 4. 跨模組集團保險全景檢視表 (F30 ↔ F10 金控壽險控制力)
CREATE VIEW IF NOT EXISTS v_f30_holding_insurer_summary AS
SELECT 
    h.holding_name,
    h.group_assets_billion,
    i.insurer_name,
    i.insurer_type,
    i.actuary_count,
    i.underwriting_count,
    i.claim_count
FROM f10_financial_holdings h
JOIN f30_insurance_institutions i 
  ON (h.holding_name LIKE '%' || REPLACE(REPLACE(i.insurer_name, '股份有限公司', ''), '人壽保險', '') || '%'
      OR h.subsidiaries_text LIKE '%' || REPLACE(i.insurer_name, '股份有限公司', '') || '%');
```

---

## 4. 基礎 CLI 與 Python API 介面規格

* **核心 API 函式 (`commands_f30.py`)**：
  * `run_f30_etl(...) -> Dict[str, Any]`：執行全量保險資料集入庫。
  * `query_insurance_institutions(db_path, limit, insurer_type) -> List[Dict[str, Any]]`：查詢保險機構與人力。
  * `query_complaint_trends(db_path, limit) -> List[Dict[str, Any]]`：查詢全台保險申訴趨勢。
  * `query_compensation_fund(db_path, limit) -> List[Dict[str, Any]]`：查詢特別補償基金收支。
* **CLI 指令**：
  * `fsc insurer list`：保險機構名錄與精算人力排行。
  * `fsc insurer complaints`：保險申訴與爭議和解趨勢。
  * `fsc insurer fund`：特別補償基金收支。
