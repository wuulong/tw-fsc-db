-- ==============================================================================
-- 🏛️ 金融監督管理委員會 (GOV-A21) 專屬業務資料庫全量 Schema (schema.sql)
-- 規範：遵循 [SPC-007] 通用五大基石介面，100% 零重複資料，一律外鍵/關聯引用母大腦。
-- ==============================================================================

-- 1. 金管會核心業務主表 (金融機構、公開發行公司、裁罰紀錄等通用骨架)
CREATE TABLE IF NOT EXISTS fsc_business_records (
    record_uid TEXT PRIMARY KEY,          -- 主碼: FSC_[SERIES]_[ID]
    agency_oid TEXT NOT NULL,             -- 通用基石一: 發布單位 OID (外鍵對齊 master_agencies.sqlite)
    record_title TEXT NOT NULL,           -- 業務紀錄名稱 (如金融機構名錄、許可案件、行政裁罰)
    admin_code TEXT,                      -- 通用基石二: 6碼行政區碼 (外鍵對齊 universal_keys.sqlite)
    river_id TEXT,                        -- 通用基石三: 122條水系代碼 (外鍵對齊 universal_keys.sqlite)
    station_id TEXT,                      -- 通用基石三: 監測站代碼
    tax_id TEXT,                          -- 通用基石四: 8碼金融機構/上市公司統編
    pub_date TEXT,                        -- 通用基石五: 發布日期
    updated_at TEXT NOT NULL,             -- 通用基石五: ISO-8601 時間戳
    attributes_json TEXT                  -- 彈性 JSON 擴充金箱
);
CREATE INDEX IF NOT EXISTS idx_fsc_agency_oid ON fsc_business_records(agency_oid);
CREATE INDEX IF NOT EXISTS idx_fsc_admin_code ON fsc_business_records(admin_code);
CREATE INDEX IF NOT EXISTS idx_fsc_tax_id ON fsc_business_records(tax_id);

-- 2. Pillar 1: 金融機構名錄與資產品質主表
CREATE TABLE IF NOT EXISTS f10_financial_institutions (
    institution_id TEXT PRIMARY KEY,       -- 機構代號 (如 004 臺灣銀行, 012 台北富邦)
    bank_name TEXT NOT NULL,               -- 機構全銜 (如 臺灣銀行股份有限公司)
    tax_id TEXT NOT NULL,                  -- 通用基石四: 8碼公司統編 (如 03795505)
    agency_oid TEXT NOT NULL,              -- 通用基石一: 監理機關 OID (銀行局 2.16.886.101.20003.20022.20001)
    institution_type TEXT NOT NULL,        -- 機構類別 (本國銀行, 外國銀行在臺分行, 信用合作社, 票券公司)
    headquarters_addr TEXT,                -- 總行營業地址
    admin_code TEXT,                       -- 通用基石二: 6碼行政區碼 (如 100005)
    telephone TEXT,                        -- 連絡電話
    website TEXT,                          -- 官方網站
    updated_at TEXT NOT NULL,              -- 通用基石五: ISO-8601 時間戳
    attributes_json TEXT                   -- 彈性 JSON (資本額, 董事長, 總經理, 許可字號)
);
CREATE INDEX IF NOT EXISTS idx_f10_tax_id ON f10_financial_institutions(tax_id);
CREATE INDEX IF NOT EXISTS idx_f10_admin_code ON f10_financial_institutions(admin_code);

-- 3. Pillar 2: 公開發行公司與月營收主表
CREATE TABLE IF NOT EXISTS f20_public_companies (
    company_code TEXT PRIMARY KEY,         -- 股票/公司代號 (如 2330, 2881)
    company_name TEXT NOT NULL,            -- 公司名稱 (如 台灣積體電路製造股份有限公司)
    tax_id TEXT NOT NULL,                  -- 通用基石四: 8碼統一編號
    market_type TEXT NOT NULL,             -- 市場類別 (上市, 上櫃, 興櫃, 公開發行)
    industry_category TEXT,                -- 產業類別 (半導體業, 金融保險業等)
    paid_in_capital REAL,                  -- 實收資本額 (元)
    chairman TEXT,                         -- 董事長
    general_manager TEXT,                  -- 總經理
    spokesperson TEXT,                     -- 發言人
    updated_at TEXT NOT NULL,              -- 通用基石五: ISO-8601
    attributes_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_f20_tax_id ON f20_public_companies(tax_id);

CREATE TABLE IF NOT EXISTS f21_monthly_revenues (
    revenue_uid TEXT PRIMARY KEY,          -- 主碼: REV_[年月]_[公司代號] (如 REV_202607_2330)
    company_code TEXT NOT NULL,            -- 外鍵 -> f20_public_companies(company_code)
    tax_id TEXT NOT NULL,                  -- 通用基石四: 8碼統編
    revenue_year_month TEXT NOT NULL,      -- 營收年月 (YYYY-MM)
    current_month_revenue REAL,            -- 當月營業收入 (千元)
    last_month_revenue REAL,               -- 上月營收 (千元)
    last_year_same_month_revenue REAL,     -- 去年同期營收 (千元)
    mom_growth_rate REAL,                  -- 上月比較增減 (%)
    yoy_growth_rate REAL,                  -- 去年同月比較增減 (%)
    updated_at TEXT NOT NULL,              -- ISO-8601
    FOREIGN KEY(company_code) REFERENCES f20_public_companies(company_code)
);
CREATE INDEX IF NOT EXISTS idx_f21_ym ON f21_monthly_revenues(revenue_year_month);
CREATE INDEX IF NOT EXISTS idx_f21_tax_id ON f21_monthly_revenues(tax_id);

-- 4. Pillar 5: 重大裁罰與消保爭議評議表
CREATE TABLE IF NOT EXISTS f50_sanctions (
    sanction_uid TEXT PRIMARY KEY,         -- 主碼: SAN_[日期]_[序號]
    sanction_date TEXT NOT NULL,           -- 處分日期 (YYYY-MM-DD)
    target_institution TEXT NOT NULL,      -- 受處分機構全銜
    tax_id TEXT,                           -- 通用基石四: 8碼統編 (若為金融機構則強制對齊)
    sanction_type TEXT NOT NULL,           -- 處分種類 (罰鍰, 糾正, 限制業務, 解除職務)
    penalty_amount INTEGER DEFAULT 0,      -- 罰鍰金額 (新臺幣元)
    law_violated TEXT,                     -- 違反法規 (如 銀行法第61條之1、洗錢防制法)
    summary TEXT NOT NULL,                 -- 處分違法事由主文
    link_url TEXT,                         -- 官方裁罰公文公告網址
    updated_at TEXT NOT NULL               -- ISO-8601
);
CREATE INDEX IF NOT EXISTS idx_f50_tax_id ON f50_sanctions(tax_id);
CREATE INDEX IF NOT EXISTS idx_f50_date ON f50_sanctions(sanction_date);

CREATE TABLE IF NOT EXISTS f51_ombudsman_cases (
    case_uid TEXT PRIMARY KEY,             -- 主碼: OMB_[年度季度]_[機構代號]
    year_quarter TEXT NOT NULL,            -- 統計季度 (如 2026-Q2)
    institution_name TEXT NOT NULL,        -- 金融服務業名稱
    tax_id TEXT,                           -- 8碼統編
    industry_type TEXT NOT NULL,           -- 業別 (銀行業, 壽險業, 產險業, 證期業)
    complaint_count INTEGER DEFAULT 0,     -- 申訴件數
    ombudsman_count INTEGER DEFAULT 0,     -- 申請評議件數
    dispute_category TEXT,                 -- 爭議主要類型 (理賠爭議, 契約變更, 授信額度)
    resolution_status TEXT,                -- 評議成立/撤回/不成立統計
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f51_yq ON f51_ombudsman_cases(year_quarter);
CREATE INDEX IF NOT EXISTS idx_f51_tax_id ON f51_ombudsman_cases(tax_id);

-- 5. Pillar 4: 金融檢查缺失倒排檢索虛擬表
CREATE VIRTUAL TABLE IF NOT EXISTS f41_exam_deficiencies_fts USING fts5(
    deficiency_uid UNINDEXED,              -- 缺失唯一碼
    industry_type,                         -- 金融業別 (外國銀行, 證券商, 壽險公司, 產險公司)
    year,                                  -- 年度
    category_title,                        -- 缺失類別 (防制洗錢, 授信風控, 資訊安全, 內控制度)
    deficiency_text,                       -- 缺失詳細描述與改善要求
    regulatory_reference                   -- 參照法條
);

-- 6. Pillar 6: VASP 虛擬資產平台合規名冊種子表
CREATE TABLE IF NOT EXISTS f61_vasp_compliance_registry (
    vasp_id TEXT PRIMARY KEY,              -- VASP 編號 (如 VASP_001)
    brand_name TEXT NOT NULL,              -- 品牌/平台名稱 (如 幣託, 麥達斯, 派網等)
    company_name TEXT NOT NULL,            -- 登記法人全銜 (如 幣託科技股份有限公司)
    tax_id TEXT NOT NULL,                  -- 通用基石四: 8碼統一編號
    compliance_date TEXT NOT NULL,         -- 完成洗防遵循聲明日期 (YYYY-MM-DD)
    registered_addr TEXT,                  -- 登記營業地址
    admin_code TEXT,                       -- 6碼行政區碼
    status TEXT DEFAULT 'COMPLIANT',       -- 狀態 (COMPLIANT, WITHDRAWN)
    updated_at TEXT NOT NULL,              -- ISO-8601
    attributes_json TEXT                   -- 營運負責人, 資本額
);
CREATE INDEX IF NOT EXISTS idx_f61_tax_id ON f61_vasp_compliance_registry(tax_id);

