-- ==============================================================================
-- 🏛️ F40: 金融檢查與重大缺失智庫 Schema (f40_inspection_bureau_db)
-- 版本: v1.0.0 (業務本位粗粒度聚合架構 + 地面真值齊備)
-- ==============================================================================

-- 1. 金融機構實地檢查重大缺失明細表
CREATE TABLE IF NOT EXISTS f40_exam_deficiencies (
    deficiency_uid TEXT PRIMARY KEY,      -- DEF_{sector}_{year}_{half}_{hash}
    target_sector TEXT NOT NULL,          -- 受檢業別: HOLDING(金控公司), FOREIGN_BANK(外銀在臺分行), DOMESTIC_BANK(本國銀行)
    eval_year TEXT NOT NULL,              -- 檢查年度 (ISO: YYYY)
    half_year TEXT NOT NULL,              -- 上半年 / 下半年 / 全年
    business_category TEXT NOT NULL,      -- 業務項目 (如 內部管理, 子公司管理, 公司治理, 風險管理, 授信業務, 防制洗錢)
    deficiency_pattern TEXT NOT NULL,     -- 缺失態樣 (核心違規摘要)
    deficiency_detail TEXT,               -- 缺失具體情節
    improvement_action TEXT,              -- 改善作法與遵循法令
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f40_sector ON f40_exam_deficiencies(target_sector);
CREATE INDEX IF NOT EXISTS idx_f40_year ON f40_exam_deficiencies(eval_year);
CREATE INDEX IF NOT EXISTS idx_f40_category ON f40_exam_deficiencies(business_category);

-- 2. 檢查局重大缺失全文檢索虛擬表 (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS f40_deficiencies_fts USING fts5(
    deficiency_uid UNINDEXED,
    target_sector UNINDEXED,
    business_category,
    deficiency_pattern,
    deficiency_detail,
    improvement_action,
    tokenize='unicode61'
);

-- 3. 檢查局檢查性質與受檢機構年度執行統計表
CREATE TABLE IF NOT EXISTS f40_inspection_execution (
    stat_uid TEXT PRIMARY KEY,            -- EXEC_{year}_{exam_type}_{sector}
    eval_year TEXT NOT NULL,              -- 統計年度 (ISO: YYYY)
    exam_type TEXT NOT NULL,              -- 檢查性質 (一般檢查, 專案檢查)
    target_sector TEXT NOT NULL,          -- 金融業別 (金控公司, 本國銀行, 外國銀行在臺分行, 產險公司, 壽險公司)
    inspected_count INTEGER NOT NULL,     -- 受檢機構家數
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f40_exec_year ON f40_inspection_execution(eval_year);

-- 4. 業務項目高頻缺失分析檢視表
CREATE VIEW IF NOT EXISTS v_f40_deficiency_category_summary AS
SELECT 
    target_sector,
    business_category,
    COUNT(*) AS deficiency_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM f40_exam_deficiencies d2 WHERE d2.target_sector = d1.target_sector), 2) AS category_pct
FROM f40_exam_deficiencies d1
GROUP BY target_sector, business_category
ORDER BY target_sector, deficiency_count DESC;
