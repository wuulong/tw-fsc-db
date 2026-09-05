-- ==============================================================================
-- 🏛️ F00: 金管會母大腦全域實體整合樞紐、拓樸網絡與元資料治理 Schema
-- ==============================================================================

-- 1. 全域子模組系統元資料表
CREATE TABLE IF NOT EXISTS sys_module_metadata (
    module_id TEXT NOT NULL,              -- 模組代號 (如 f10_banking_credit_db, f20_securities_markets_db)
    module_name TEXT NOT NULL,            -- 模組中文名稱
    table_name TEXT NOT NULL,             -- 實體資料表名稱
    record_count INTEGER DEFAULT 0,       -- 目前資料筆數
    schema_version TEXT DEFAULT '2.0.0',  -- 規格版號
    last_updated TEXT NOT NULL,           -- ISO-8601 時間戳
    PRIMARY KEY (module_id, table_name)
);

-- 2. 全域金融法人實體權威登記主表 (Universal Entity Registry)
CREATE TABLE IF NOT EXISTS f00_entity_registry (
    master_uid TEXT PRIMARY KEY,          -- 權威實體識別碼: ENT_{tax_id} 或 ENT_{stock_code} 或 MD5(canonical_name)
    tax_id TEXT UNIQUE,                   -- 財政部 8 碼營利事業統一編號
    stock_code TEXT UNIQUE,               -- 證券公開發行 4 碼股票代號 (F20)
    banking_code TEXT,                    -- 銀行機構金融代碼 (F10, 3-7碼)
    insurance_code TEXT,                  -- 保險機構代碼 (F30)
    vasp_reg_no TEXT,                     -- 虛擬資產洗錢防制聲明登記代號 (F60)
    canonical_name TEXT NOT NULL,         -- 權威法定全銜 (如 '國泰金融控股股份有限公司')
    common_alias TEXT,                    -- 常見商業簡稱與別名 (如 '國泰金控, 國泰金, Cathay FHC')
    entity_class TEXT NOT NULL,           -- 實體類別: FHC(金控), BANK(銀行), SECURITIES(證券), INSURER(保險), LISTED(一般上市櫃), VASP(虛擬資產)
    is_financial_institution INTEGER DEFAULT 0, -- 是否為受特許監理之金融機構 (0: 否, 1: 是)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f00_ent_tax ON f00_entity_registry(tax_id);
CREATE INDEX IF NOT EXISTS idx_f00_ent_stock ON f00_entity_registry(stock_code);
CREATE INDEX IF NOT EXISTS idx_f00_ent_class ON f00_entity_registry(entity_class);

-- 3. 跨模組集團股權與控制力拓樸關聯表 (Conglomerate Ownership & Control Network)
CREATE TABLE IF NOT EXISTS f00_entity_relations (
    relation_uid TEXT PRIMARY KEY,        -- REL_{parent_uid}_{child_uid}_{type}
    parent_uid TEXT NOT NULL,             -- 母公司 / 金控 / 最終控制人 UID
    child_uid TEXT NOT NULL,              -- 子公司 / 轉投資事業 / 被持股公司 UID
    relation_type TEXT NOT NULL,          -- 關係類別: SUBSIDIARY(100%全資子公司), MAJOR_SHAREHOLDER(逾10%大股東), AFFILIATE(轉投資關係企業)
    shareholding_ratio REAL,              -- 持股比例 (%)
    control_level TEXT DEFAULT 'DIRECT',  -- DIRECT(直接持股), INDIRECT(間接控制)
    effective_date TEXT,                  -- 申報生效日 (ISO: YYYY-MM-DD)
    updated_at TEXT NOT NULL,
    FOREIGN KEY(parent_uid) REFERENCES f00_entity_registry(master_uid),
    FOREIGN KEY(child_uid) REFERENCES f00_entity_registry(master_uid)
);
CREATE INDEX IF NOT EXISTS idx_f00_rel_parent ON f00_entity_relations(parent_uid);
CREATE INDEX IF NOT EXISTS idx_f00_rel_child ON f00_entity_relations(child_uid);

-- 4. 全域監理風險特徵與裁罰計分表 (Cross-Domain Risk & Sanction Ledger)
CREATE TABLE IF NOT EXISTS f00_supervisory_radar (
    radar_uid TEXT PRIMARY KEY,           -- RDR_{entity_uid}_{year_month}
    entity_uid TEXT NOT NULL,             -- 關聯至 f00_entity_registry
    eval_year_month TEXT NOT NULL,        -- 評估年月 (ISO: YYYY-MM)
    total_sanctions_count INTEGER DEFAULT 0, -- 歷史重大裁罰累計次數 (F50)
    total_penalty_fine_ntd REAL DEFAULT 0,   -- 累計裁罰金額 (新臺幣元, F50)
    exam_deficiency_count INTEGER DEFAULT 0, -- 檢查局重大檢查缺失累計次數 (F40)
    consumer_dispute_count INTEGER DEFAULT 0,-- 評議中心申訴受理件數 (F50)
    npl_ratio REAL,                       -- 當期銀行逾放比率 (F10)
    revenue_growth_yoy REAL,              -- 當期上市營收年增率 (F20)
    composite_risk_level TEXT NOT NULL,   -- 綜合監理風險燈號: GREEN(穩健), YELLOW(關注), RED(警戒)
    updated_at TEXT NOT NULL,
    FOREIGN KEY(entity_uid) REFERENCES f00_entity_registry(master_uid)
);
CREATE INDEX IF NOT EXISTS idx_f00_rdr_risk ON f00_supervisory_radar(composite_risk_level);

-- 5. 全域 FTS5 全文倒排索引虛擬表
CREATE VIRTUAL TABLE IF NOT EXISTS fts_fsc_global USING fts5(
    domain_code UNINDEXED,                -- 業務代號 (F10, F20, F30, F40, F50, F60)
    entity_type UNINDEXED,                -- 實體類型 (HOLDING, BANK, COMPANY, INSURER, INSPECTION, SANCTION, VASP)
    entity_id UNINDEXED,                  -- 實體主鍵 (統編、代號或名稱)
    primary_name,                         -- 實體主要名稱 (如 '國泰金控', '臺灣銀行', '台積電')
    secondary_info,                       -- 次要描述 (如 子公司、董監事、行業別、處分事由)
    detail_payload UNINDEXED,             -- 緊湊 JSON 資料快照
    tokenize='unicode61'
);

-- 6. 跨模組 360 度全景實體監理檢視表 (Single Entity 360° Supervisory View)
-- 匯流 F10 (金控資產/銀行放款/土融集中/信用卡簽帳)、F20 (上市營收/年增率/P/E/殖利率) 與 F30 (保險精算/核保/理賠專業人力)
CREATE VIEW IF NOT EXISTS v_f00_entity_360_profile AS
SELECT 
    e.master_uid,
    e.canonical_name,
    e.common_alias,
    e.tax_id,
    e.stock_code,
    e.entity_class,
    h.group_assets_billion AS fhc_assets_billion,
    h.subsidiaries_count AS fhc_subsidiaries_count,
    b.loan_total AS bank_loan_total,
    b.npl_ratio AS bank_npl_ratio,
    b.coverage_ratio AS bank_coverage_ratio,
    l.land_loan_balance AS bank_land_loan_balance,
    l.land_loan_ratio AS bank_land_loan_ratio,
    c.signing_amount_million AS cc_signing_amount,
    c.active_card_ratio AS cc_active_card_ratio,
    r.current_month_revenue AS listed_monthly_revenue,
    r.yoy_growth_rate AS listed_revenue_yoy,
    v.pe_ratio AS listed_pe_ratio,
    v.dividend_yield AS listed_dividend_yield,
    v.pb_ratio AS listed_pb_ratio,
    ins.insurer_type,
    ins.inner_staff_count AS insurer_inner_staff,
    ins.field_agent_count AS insurer_field_agent,
    ins.actuary_count AS insurer_actuary_count,
    ins.underwriting_count AS insurer_underwriting_count,
    ins.claim_count AS insurer_claim_count,
    omb.complaint_count AS ombudsman_complaint_count,
    omb.complaint_ratio AS ombudsman_complaint_ratio,
    radar.composite_risk_level,
    radar.exam_deficiency_count,
    radar.total_sanctions_count,
    radar.total_penalty_fine_ntd
FROM f00_entity_registry e
LEFT JOIN f10_financial_holdings h ON e.canonical_name LIKE '%' || h.holding_name || '%'
LEFT JOIN f10_bank_asset_quality b ON e.canonical_name LIKE '%' || b.bank_name || '%'
LEFT JOIN f10_land_collateral_loans l ON b.bank_name = l.bank_name
LEFT JOIN f10_credit_card_operations c ON b.bank_name = c.institution_name
LEFT JOIN f20_monthly_revenues r ON e.stock_code = r.company_code
LEFT JOIN f20_market_valuations v ON e.stock_code = v.company_code
LEFT JOIN f30_insurance_institutions ins ON (e.canonical_name = ins.insurer_name OR ins.insurer_name LIKE '%' || e.canonical_name || '%')
LEFT JOIN f50_ombudsman_cases omb ON (omb.institution_name LIKE '%' || e.canonical_name || '%' OR e.canonical_name LIKE '%' || omb.institution_name || '%')
LEFT JOIN f00_supervisory_radar radar ON e.master_uid = radar.entity_uid;

-- 7. 跨模組集團控制力與股權網絡全景檢視表 (Conglomerate & Major Ownership Map)
CREATE VIEW IF NOT EXISTS v_f00_group_conglomerate_map AS
SELECT 
    r.relation_uid,
    r.relation_type,
    r.control_level,
    r.shareholding_ratio,
    p.master_uid AS parent_uid,
    p.canonical_name AS parent_name,
    p.entity_class AS parent_class,
    c.master_uid AS child_uid,
    c.canonical_name AS child_name,
    c.entity_class AS child_class,
    c.stock_code AS child_stock_code,
    r.effective_date,
    r.updated_at
FROM f00_entity_relations r
JOIN f00_entity_registry p ON r.parent_uid = p.master_uid
JOIN f00_entity_registry c ON r.child_uid = c.master_uid;
