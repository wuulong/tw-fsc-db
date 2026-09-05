-- ==============================================================================
-- 🏛️ F30: 保險市場與精算風險資料庫 Schema (f30_insurance_actuarial_db)
-- 版本: v1.0.0 (業務本位粗粒度聚合架構 + 地面真值齊備)
-- ==============================================================================

-- 1. 保險機構專業人力結構與精算配置表
CREATE TABLE IF NOT EXISTS f30_insurance_institutions (
    insurer_name TEXT PRIMARY KEY,        -- 保險機構法定全銜 (如 國泰人壽保險股份有限公司, 富邦產物保險股份有限公司)
    insurer_type TEXT NOT NULL,           -- LIFE(人壽保險), PROPERTY(產物保險), COOP(合作社)
    inner_staff_count INTEGER,            -- 內勤從業人員數
    field_agent_count INTEGER,            -- 外勤從業人員數
    underwriting_count INTEGER,           -- 核保專業人員數
    claim_count INTEGER,                  -- 理賠專業人員數
    actuary_count INTEGER,                -- 精算專業人員數
    report_date TEXT NOT NULL,            -- 基準統計日期 (ISO: YYYY-MM-DD)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
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
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f30_eval_year ON f30_insurance_complaint_trends(eval_year);

-- 3. 汽車交通事故特別補償基金運作表
CREATE TABLE IF NOT EXISTS f30_special_compensation_fund (
    stat_year TEXT PRIMARY KEY,           -- 統計年度 (ISO: YYYY)
    contribution_income_thousand REAL,    -- 分擔額收入 (千元)
    compensation_expense_thousand REAL,   -- 補償支出 (千元)
    compensated_cases INTEGER,            -- 補償件數
    avg_compensation_thousand REAL,       -- 平均每件補償金額 (千元)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f30_fund_year ON f30_special_compensation_fund(stat_year);

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
      OR h.subsidiaries_text LIKE '%' || REPLACE(REPLACE(i.insurer_name, '股份有限公司', ''), '（115.1.1合併前）', '') || '%');
