-- ==============================================================================
-- 🏛️ F50: 法律事務、處分裁罰與評議爭議智庫 Schema (f50_sanctions_legal_db)
-- 版本: v1.0.0 (真實處分書 499 筆全量落地 + FTS5 違規事實檢索 + 評議爭議追蹤)
-- ==============================================================================

-- 1. 全域金融重大裁罰處分實體表
CREATE TABLE IF NOT EXISTS f50_sanctions (
    sanction_uid TEXT PRIMARY KEY,        -- SNC_{doc_no_hash}
    doc_no TEXT NOT NULL,                 -- 主管機關發文字號
    sanction_date TEXT NOT NULL,          -- 處分日期 (ISO: YYYY-MM-DD)
    target_name TEXT NOT NULL,            -- 受處分人/機構全銜
    tax_id TEXT,                          -- 統一編號
    penalty_fine_ntd REAL DEFAULT 0.0,    -- 罰鍰金額 (新臺幣元)
    agency_bureau TEXT NOT NULL,          -- 業務局處 (銀行局, 證券期貨局, 保險局, 檢查局)
    main_subject TEXT NOT NULL,           -- 主旨
    violation_facts TEXT,                 -- 事實情節
    legal_basis TEXT,                     -- 法令依據
    source_url TEXT,                      -- 原處分書連結
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f50_date ON f50_sanctions(sanction_date);
CREATE INDEX IF NOT EXISTS idx_f50_target ON f50_sanctions(target_name);
CREATE INDEX IF NOT EXISTS idx_f50_tax ON f50_sanctions(tax_id);

-- 2. 違規事實法條 FTS5 全文倒排檢索虛擬表
CREATE VIRTUAL TABLE IF NOT EXISTS f50_sanctions_fts USING fts5(
    sanction_uid UNINDEXED,
    doc_no,
    target_name,
    main_subject,
    violation_facts,
    legal_basis,
    tokenize='unicode61'
);

-- 3. 金融消費評議申訴統計主表
CREATE TABLE IF NOT EXISTS f50_ombudsman_cases (
    case_uid TEXT PRIMARY KEY,            -- OMB_{period}_{bank_hash}
    start_date TEXT NOT NULL,             -- 統計起日 (ISO: YYYY-MM-DD)
    end_date TEXT NOT NULL,               -- 統計迄日 (ISO: YYYY-MM-DD)
    institution_name TEXT NOT NULL,       -- 爭議機構名稱
    complaint_count INTEGER NOT NULL,     -- 申訴件數
    complaint_ratio REAL,                 -- 案件比率 (%)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f50_omb_inst ON f50_ombudsman_cases(institution_name);

-- 4. 機構累計裁罰與罰鍰排行榜檢視表
CREATE VIEW IF NOT EXISTS v_f50_institution_sanction_summary AS
SELECT 
    target_name,
    COUNT(*) AS total_sanctions_count,
    SUM(penalty_fine_ntd) AS total_penalty_fine_ntd,
    MAX(sanction_date) AS latest_sanction_date
FROM f50_sanctions
GROUP BY target_name
ORDER BY total_penalty_fine_ntd DESC;
