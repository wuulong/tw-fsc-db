-- ==============================================================================
-- 🏛️ F10: 銀行與信用金融資料庫 Schema (f10_banking_credit_db)
-- 版本: v1.0.0 (五大資料表地面真值齊備 + SQLite 原生 UDF 全面下沉)
-- ==============================================================================

-- 1. 金融控股公司及子公司明細表
CREATE TABLE IF NOT EXISTS f10_financial_holdings (
    holding_name TEXT PRIMARY KEY,        -- 金控公司名稱 (如 華南金融控股公司, 富邦金融控股公司)
    approved_date TEXT,                   -- 核准設立日期 (ISO 8601: YYYY-MM-DD)
    opening_date TEXT,                    -- 開業日期 (ISO 8601: YYYY-MM-DD)
    group_assets_billion REAL,            -- 集團資產 (單位: 10億元新臺幣)
    group_net_worth_billion REAL,         -- 集團淨值 (單位: 10億元新臺幣)
    subsidiaries_text TEXT,               -- 子公司清單字串
    subsidiaries_count INTEGER,           -- 子公司數量統計 (UDF COUNT_DELIMITED)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

CREATE INDEX IF NOT EXISTS idx_f10_fhc_assets ON f10_financial_holdings(group_assets_billion);

-- 2. 本國銀行營運與資產品質表 (Banking12)
CREATE TABLE IF NOT EXISTS f10_bank_asset_quality (
    bank_name TEXT PRIMARY KEY,           -- 銀行名稱 (如 臺灣銀行, 臺灣土地銀行)
    deposit_amount REAL,                  -- 存款總額 (百萬元)
    pretax_profit REAL,                   -- 稅前盈餘 (百萬元)
    loan_total REAL,                      -- 放款總額 (百萬元)
    overdue_loan_total REAL,              -- 逾期放款總額 (百萬元)
    allowance_bad_debt REAL,              -- 貼現及放款提列之備抵呆帳 (百萬元)
    net_worth REAL,                       -- 淨值 (百萬元)
    npl_ratio REAL,                       -- 逾放比率 (%)
    coverage_ratio REAL,                  -- 備抵呆帳覆蓋率: 備抵呆帳/逾期放款 (%)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

CREATE INDEX IF NOT EXISTS idx_f10_npl ON f10_bank_asset_quality(npl_ratio);
CREATE INDEX IF NOT EXISTS idx_f10_coverage ON f10_bank_asset_quality(coverage_ratio);

-- 3. 土地擔保放款餘額與集中度表 (f10_land_collateral_loans)
CREATE TABLE IF NOT EXISTS f10_land_collateral_loans (
    bank_name TEXT PRIMARY KEY,           -- 金融機構名稱
    land_loan_balance REAL,               -- 以土地為擔保品之放款餘額 (百萬元)
    total_loan_including_call REAL,       -- 放款總額含催收款 (百萬元)
    land_loan_ratio REAL,                 -- 土地放款佔放款總額比率 (%) (UDF BANK_72_2_RATIO)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

CREATE INDEX IF NOT EXISTS idx_f10_land_loan_ratio ON f10_land_collateral_loans(land_loan_ratio);

-- 4. 信用卡業務與財務資訊表 (f10_credit_card_operations)
CREATE TABLE IF NOT EXISTS f10_credit_card_operations (
    institution_name TEXT PRIMARY KEY,    -- 發卡機構名稱 (銀行別)
    cards_effective INTEGER,              -- 流通卡數 (張)
    cards_active INTEGER,                 -- 有效卡數 (張)
    cards_issued_month INTEGER,           -- 當月發卡數
    cards_revoked_month INTEGER,          -- 當月停卡數
    signing_amount_million REAL,          -- 當月簽帳金額 (百萬元)
    revolving_balance_million REAL,       -- 循環信用餘額 (百萬元)
    delinquent_over_3m_million REAL,      -- 逾期三個月以上帳款 (百萬元)
    delinquent_over_6m_million REAL,      -- 逾期六個月以上帳款 (百萬元)
    active_card_ratio REAL,               -- 活卡率 (%) = 有效卡數 / 流通卡數 * 100
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

CREATE INDEX IF NOT EXISTS idx_f10_cc_signing ON f10_credit_card_operations(signing_amount_million);
CREATE INDEX IF NOT EXISTS idx_f10_cc_active_ratio ON f10_credit_card_operations(active_card_ratio);

-- 5. 聯徵中心全台企業貸款趨勢表 (f10_corporate_loan_trends)
CREATE TABLE IF NOT EXISTS f10_corporate_loan_trends (
    year_month TEXT PRIMARY KEY,          -- 年月份 (ISO: YYYY-MM)
    loan_entity_count INTEGER,            -- 企業貸款總家數
    loan_total_thousand REAL,             -- 企業貸款總金額 (仟元)
    loan_avg_thousand REAL,               -- 企業貸款平均金額 (仟元)
    loan_total_billion REAL,              -- 企業貸款總金額 (換算十億元)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

CREATE INDEX IF NOT EXISTS idx_f10_corp_year_month ON f10_corporate_loan_trends(year_month);

-- 6. 跨表彙整檢視表: 金控與旗下銀行總覽 (v_f10_holding_banking_summary)
CREATE VIEW IF NOT EXISTS v_f10_holding_banking_summary AS
SELECT 
    h.holding_name,
    h.group_assets_billion,
    h.group_net_worth_billion,
    h.subsidiaries_count,
    b.bank_name,
    b.deposit_amount,
    b.loan_total,
    b.npl_ratio,
    b.coverage_ratio,
    l.land_loan_balance,
    l.land_loan_ratio,
    c.signing_amount_million AS cc_signing_amount,
    c.active_card_ratio AS cc_active_ratio
FROM f10_financial_holdings h
LEFT JOIN f10_bank_asset_quality b 
  ON h.subsidiaries_text LIKE '%' || b.bank_name || '%'
LEFT JOIN f10_land_collateral_loans l
  ON b.bank_name = l.bank_name
LEFT JOIN f10_credit_card_operations c
  ON b.bank_name = c.institution_name;

-- 7. 銀行信用風險監理綜合指標檢視表 (v_f10_bank_credit_risk_profile)
-- 結合放款逾放比、備抵呆帳、土地融資比率與信用卡逾期款，透過 UDF RISK_BADGE 動態輸出監理燈號
CREATE VIEW IF NOT EXISTS v_f10_bank_credit_risk_profile AS
SELECT 
    b.bank_name,
    b.loan_total,
    b.npl_ratio,
    b.coverage_ratio,
    COALESCE(l.land_loan_balance, 0.0) AS land_loan_balance,
    COALESCE(l.land_loan_ratio, 0.0) AS land_loan_ratio,
    COALESCE(c.signing_amount_million, 0.0) AS cc_monthly_signing,
    COALESCE(c.delinquent_over_3m_million, 0.0) AS cc_delinquent_3m,
    RISK_BADGE(b.npl_ratio, b.coverage_ratio) AS supervisory_risk_badge
FROM f10_bank_asset_quality b
LEFT JOIN f10_land_collateral_loans l ON b.bank_name = l.bank_name
LEFT JOIN f10_credit_card_operations c ON b.bank_name = c.institution_name;