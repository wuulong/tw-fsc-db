-- ==============================================================================
-- 🏛️ F60: 金融科技、虛擬資產平台 (VASP) 與永續金融智庫 Schema (f60_fintech_vasp_db)
-- 版本: v1.0.0 (真實 VASP 洗防名冊 + 監理沙盒創新實驗 + 35年溫室氣體碳排時序)
-- ==============================================================================

-- 1. VASP 虛擬資產平台業者洗防合規主表
CREATE TABLE IF NOT EXISTS f60_vasp_compliance_registry (
    vasp_id TEXT PRIMARY KEY,              -- VASP 編號 (如 VASP-001)
    brand_name TEXT NOT NULL,              -- 品牌/平台名稱 (如 MaiCoin / MAX)
    company_name TEXT NOT NULL,            -- 登記法人全銜 (如 現代財富科技有限公司)
    tax_id TEXT NOT NULL,                  -- 通用基石四: 8碼統一編號
    compliance_date TEXT NOT NULL,         -- 完成洗防遵循聲明日期 (YYYY-MM-DD)
    business_type TEXT NOT NULL,           -- 業務型態 (買賣、交換、託管)
    fiat_custody_bank TEXT,                -- 法幣信託代管銀行
    status TEXT DEFAULT 'COMPLIANT',       -- 狀態 (COMPLIANT, WITHDRAWN, SUSPENDED)
    updated_at TEXT NOT NULL,              -- ISO-8601 時間戳
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f60_vasp_tax ON f60_vasp_compliance_registry(tax_id);
CREATE INDEX IF NOT EXISTS idx_f60_vasp_status ON f60_vasp_compliance_registry(status);

-- 2. 金融科技監理沙盒創新實驗主表
CREATE TABLE IF NOT EXISTS f60_fintech_sandbox (
    case_no TEXT PRIMARY KEY,              -- 核准字號 (如 FS-2020-001)
    applicant TEXT NOT NULL,               -- 申請機構 (如 好好投資科技股份有限公司)
    partner_institution TEXT NOT NULL,     -- 合作金融機構 (如 台北富邦商業銀行)
    partner_tax_id TEXT,                   -- 合作金融機構統編
    experiment_title TEXT NOT NULL,        -- 創新實驗主題
    experiment_domain TEXT DEFAULT 'WEALTH_TECH', -- 業務領域
    approval_date TEXT NOT NULL,           -- 核准日期 (YYYY-MM-DD)
    status TEXT DEFAULT 'ACTIVE',          -- 狀態 (ACTIVE, GRADUATED, TERMINATED)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f60_sandbox_partner ON f60_fintech_sandbox(partner_institution);

-- 3. 國家溫室氣體排放與永續揭露主表
CREATE TABLE IF NOT EXISTS f60_greenhouse_gas_report (
    year INTEGER PRIMARY KEY,              -- 統計年度 (如 2024)
    co2_value REAL NOT NULL,               -- 二氧化碳排放 (千公噸)
    ch4_value REAL NOT NULL,               -- 甲烷排放 (千公噸)
    n2o_value REAL NOT NULL,               -- 氧化亞氮排放 (千公噸)
    hfcs_value REAL DEFAULT 0.0,           -- 氫氟碳化物
    pfcs_value REAL DEFAULT 0.0,           -- 全氟碳化物
    sf6_value REAL DEFAULT 0.0,            -- 六氟化硫
    nf3_value REAL DEFAULT 0.0,            -- 三氟化氮
    total_ghg_emission_value REAL NOT NULL,-- 溫室氣體毛排放總量
    co2_absorption_value REAL NOT NULL,    -- 碳匯吸收總量 (負值)
    net_ghg_emission_value REAL NOT NULL,  -- 溫室氣體淨排放總量
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);

-- 4. 創新金融科技與永續指標綜合檢視表
CREATE VIEW IF NOT EXISTS v_f60_fintech_esg_overview AS
SELECT 
    (SELECT COUNT(*) FROM f60_vasp_compliance_registry WHERE status = 'COMPLIANT') AS compliant_vasp_count,
    (SELECT COUNT(*) FROM f60_fintech_sandbox WHERE status = 'GRADUATED') AS graduated_sandbox_count,
    (SELECT COUNT(*) FROM f60_fintech_sandbox WHERE status = 'ACTIVE') AS active_sandbox_count,
    (SELECT year FROM f60_greenhouse_gas_report ORDER BY year DESC LIMIT 1) AS latest_ghg_year,
    (SELECT net_ghg_emission_value FROM f60_greenhouse_gas_report ORDER BY year DESC LIMIT 1) AS latest_net_ghg_emission;
