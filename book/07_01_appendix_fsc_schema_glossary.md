# 附錄 A：fsc.db 全庫 Schema 與 DDL 資料字典

本附錄收錄 `tw-fsc-db` 核心資料庫 `fsc.db` 中涵蓋 F00 母大腦至 F60 創新模組之全部 24 張資料表、虛擬 FTS5 倒排索引表與關聯檢視之完整 SQL DDL 定義，供系統架構師、DBA 與資料工程師隨時查閱。

---

## A.1 F00 金融機構實體母大腦 (Master Brain)

### 表 1：`f00_institutions` (金融機構母實體登記主表)
```sql
CREATE TABLE IF NOT EXISTS f00_institutions (
    institution_id TEXT PRIMARY KEY,        -- 機構統一識別碼 (若無統編則使用編碼)
    tax_id TEXT,                            -- 統一編號 (8 碼)
    official_name TEXT NOT NULL,            -- 主管機關官方登記全名
    alias_names TEXT,                       -- 常用簡稱、英文名稱或曾用名 (逗號分隔)
    category TEXT NOT NULL,                 -- 金融類別 (銀行/證券/保險/金控/投信等)
    status TEXT DEFAULT 'ACTIVE',           -- 營業狀態 (ACTIVE: 營業中, MERGED: 已消滅/合併, REVOKED: 撤銷)
    fsc_license_no TEXT,                    -- 金管會特許執照字號
    registered_address TEXT,                -- 登記營業地址
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_f00_tax_id ON f00_institutions(tax_id);
CREATE INDEX IF NOT EXISTS idx_f00_category ON f00_institutions(category);
```

### 表 2：`f00_institution_relations` (機構血緣與母子集團控制力關聯表)
```sql
CREATE TABLE IF NOT EXISTS f00_institution_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_institution_id TEXT NOT NULL,   -- 母公司/金控機構碼
    child_institution_id TEXT NOT NULL,    -- 子公司/轉投資機構碼
    relation_type TEXT NOT NULL,           -- 關係型態 (SUBSIDIARY: 子公司, BRANCH: 分行, ACQUIRED: 併購吸收)
    effective_date TEXT,                   -- 生效/併購基準日
    remarks TEXT,
    FOREIGN KEY(parent_institution_id) REFERENCES f00_institutions(institution_id),
    FOREIGN KEY(child_institution_id) REFERENCES f00_institutions(institution_id)
);
```

---

## A.2 F10 銀行機構與信用金融資料表 (Banking & Credit)

### 表 3：`f10_bank_master` (本國銀行與外商分行母名冊)
```sql
CREATE TABLE IF NOT EXISTS f10_bank_master (
    bank_code TEXT PRIMARY KEY,            -- 銀行程式碼 (3 碼)
    institution_id TEXT,                   -- 關聯至 F00 母實體
    bank_name TEXT NOT NULL,               -- 銀行名稱
    bank_type TEXT,                        -- 銀行類型 (本國銀行/外國銀行在台分行/陸資銀行)
    headquarters_address TEXT,             -- 總行地址
    swift_code TEXT,                       -- SWIFT Code
    FOREIGN KEY(institution_id) REFERENCES f00_institutions(institution_id)
);
```

### 表 4：`f10_credit_card_trends` (全台信用卡跨月簽帳動能時序表)
```sql
CREATE TABLE IF NOT EXISTS f10_credit_card_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month TEXT NOT NULL,              -- 資料年月 (YYYY-MM)
    bank_code TEXT,                        -- 銀行程式碼
    active_cards_count INTEGER,            -- 活卡數
    total_issued_cards INTEGER,            -- 總流通卡數
    monthly_retail_sales_ntd REAL,         -- 當月簽帳消費金額 (新台幣元)
    cash_advance_amount_ntd REAL,          -- 當月預借現金金額 (新台幣元)
    delinquency_ratio REAL,                -- 逾期信用貸款比率 (%)
    FOREIGN KEY(bank_code) REFERENCES f10_bank_master(bank_code)
);
CREATE INDEX IF NOT EXISTS idx_f10_card_ym ON f10_credit_card_trends(year_month);
```

### 表 5：`f10_land_financing_stats` (主要公私立銀行土地擔保融資比率表)
```sql
CREATE TABLE IF NOT EXISTS f10_land_financing_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_code TEXT NOT NULL,
    year_quarter TEXT NOT NULL,            -- 資料季度 (YYYY-Qn)
    land_loan_balance_ntd REAL,            -- 土地擔保放款餘額 (億元)
    total_loan_balance_ntd REAL,           -- 總放款餘額 (億元)
    land_loan_ratio REAL,                  -- 土地融資比率 (%)
    FOREIGN KEY(bank_code) REFERENCES f10_bank_master(bank_code)
);
```

---

## A.3 F20 證券市場與上市櫃公司資料表 (Securities & Markets)

### 表 6：`f20_listed_companies` (上市櫃公發公司核心資料表)
```sql
CREATE TABLE IF NOT EXISTS f20_listed_companies (
    symbol TEXT PRIMARY KEY,               -- 股票代號 (4~6 碼)
    company_name TEXT NOT NULL,            -- 公司名稱
    tax_id TEXT,                           -- 統一編號
    market_type TEXT,                      -- 上市 (TWSE) / 上櫃 (TPEx) / 興櫃
    industry_category TEXT,                -- 產業類別 (半導體/金融保險等)
    listing_date TEXT,                     -- 上市日期
    paid_in_capital_ntd REAL               -- 實收資本額 (元)
);
```

### 表 7：`f20_market_valuations` (本益比、殖利率與股價淨值比估值表)
```sql
CREATE TABLE IF NOT EXISTS f20_market_valuations (
    symbol TEXT PRIMARY KEY,
    trade_date TEXT NOT NULL,              -- 交易日期
    closing_price REAL,                    -- 收盤價
    pe_ratio REAL,                         -- 本益比 (P/E)
    pb_ratio REAL,                         -- 股價淨值比 (P/B)
    dividend_yield REAL,                   -- 殖利率 (%)
    is_negative_eps INTEGER DEFAULT 0,     -- 是否為虧損公司 (0: 獲利, 1: 虧損)
    FOREIGN KEY(symbol) REFERENCES f20_listed_companies(symbol)
);
```

### 表 8：`f20_major_shareholders` (董監與逾 10% 大股東持股明細表)
```sql
CREATE TABLE IF NOT EXISTS f20_major_shareholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    shareholder_hash TEXT NOT NULL,        -- 股東去識別化/法人雜湊標識
    shareholder_title TEXT,                -- 職稱 (董事長/法人董事/主要股東)
    shares_held INTEGER,                   -- 持股總數 (股)
    holding_percentage REAL,               -- 持股比例 (%)
    pledged_percentage REAL,               -- 質押比例 (%)
    FOREIGN KEY(symbol) REFERENCES f20_listed_companies(symbol)
);
```

---

## A.4 F30 保險市場與精算核保資料表 (Insurance & Actuarial)

### 表 9：`f30_insurance_companies` (產壽險機構名冊與專業人力表)
```sql
CREATE TABLE IF NOT EXISTS f30_insurance_companies (
    insurer_id TEXT PRIMARY KEY,           -- 保險業代號
    insurer_name TEXT NOT NULL,            -- 機構名稱
    insurer_type TEXT,                     -- 類型 (LIFE: 壽險, NON_LIFE: 產險, REINSURANCE: 再保)
    actuary_staff_count INTEGER,           -- 精算人員數量
    underwriter_staff_count INTEGER,       -- 核保人員數量
    claims_staff_count INTEGER,            -- 理賠人員數量
    sales_agents_count INTEGER             -- 業務員登錄人數
);
```

### 表 10：`f30_dispute_complaints_trends` (25 年跨期申訴率時序統計表)
```sql
CREATE TABLE IF NOT EXISTS f30_dispute_complaints_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,                 -- 年度
    insurer_id TEXT NOT NULL,
    complaint_cases_count INTEGER,         -- 爭議申訴總件數
    signed_premium_million_ntd REAL,       -- 簽單保費 (百萬元)
    complaint_ratio REAL,                  -- 萬分之申訴率
    FOREIGN KEY(insurer_id) REFERENCES f30_insurance_companies(insurer_id)
);
```

---

## A.5 F40 金融檢查重大缺失表與 FTS5 (Inspection Bureau)

### 表 11：`f40_inspection_findings` (金融檢查重大缺失結構化明細表)
```sql
CREATE TABLE IF NOT EXISTS f40_inspection_findings (
    finding_id TEXT PRIMARY KEY,           -- 缺失案號
    institution_type TEXT NOT NULL,        -- 查核業別 (銀行/保險/證券)
    finding_category TEXT NOT NULL,        -- 缺失維度 (內部控制/洗錢防制/資訊安全/消費者保護)
    severity_level TEXT,                   -- 嚴重度 (MAJOR: 重大, MODERATE: 中度)
    finding_summary TEXT NOT NULL,         -- 缺失態樣事實摘要
    legal_reference TEXT,                  -- 違反法規與令釋依據
    inspection_year INTEGER                -- 金檢執行年度
);
```

### 表 12：`f40_inspection_findings_fts` (缺失全文檢索 FTS5 倒排虛擬表)
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS f40_inspection_findings_fts USING fts5(
    finding_id UNINDEXED,
    finding_summary,
    legal_reference,
    tokenize = 'porter unicode61'
);
```

---

## A.6 F50 處分裁罰與金融評議資料表 (Sanctions & Legal)

### 表 13：`f50_sanction_records` (重大行政處分裁罰紀錄表)
```sql
CREATE TABLE IF NOT EXISTS f50_sanction_records (
    case_id TEXT PRIMARY KEY,              -- 裁罰處分書發文字號
    disposition_date TEXT NOT NULL,        -- 處分日期 (YYYY-MM-DD)
    entity_name TEXT NOT NULL,             -- 受處分機構或個人名稱
    tax_id TEXT,                           -- 受處分機構統編
    penalty_amount_ntd REAL,               -- 裁罰金額 (新台幣元)
    sanction_type TEXT,                    -- 處分種類 (罰鍰/糾正/停業/解除職務)
    legal_basis TEXT,                      -- 處分法令依據條文
    summary TEXT,                          -- 違法事實與處分理由要旨
    bureau TEXT                            -- 作出處分之主管局處 (銀行局/證期局/保險局/檢查局)
);
CREATE INDEX IF NOT EXISTS idx_f50_entity ON f50_sanction_records(entity_name);
CREATE INDEX IF NOT EXISTS idx_f50_date ON f50_sanction_records(disposition_date);
```

### 表 14：`f50_sanction_records_fts` (處分書全文檢索 FTS5 倒排虛擬表)
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS f50_sanction_records_fts USING fts5(
    case_id UNINDEXED,
    entity_name,
    legal_basis,
    summary,
    tokenize = 'porter unicode61'
);
```

---

## A.7 F60 金融科技創新、VASP 與永續資料表 (FinTech & ESG)

### 表 15：`f60_vasp_compliance_entities` (洗錢防制法遵聲明合規 VASP 名冊)
```sql
CREATE TABLE IF NOT EXISTS f60_vasp_compliance_entities (
    vasp_id TEXT PRIMARY KEY,              -- VASP 登記程式碼
    tax_id TEXT UNIQUE NOT NULL,           -- 公司統一編號
    company_name TEXT NOT NULL,            -- 公司中文登記全名
    brand_name TEXT,                       -- 平台品牌或交易所名稱
    compliance_declaration_date TEXT,      -- 金管會公告完成法遵聲明日
    fiat_custody_bank TEXT,                -- 新台幣法幣信託代管銀行全名
    status TEXT DEFAULT 'ACTIVE'           -- 營運狀態
);
```

### 表 16：`f60_fintech_sandbox_experiments` (監理沙盒創新實驗案實況表)
```sql
CREATE TABLE IF NOT EXISTS f60_fintech_sandbox_experiments (
    case_no TEXT PRIMARY KEY,              -- 沙盒申請案號
    applicant_name TEXT NOT NULL,          -- 申請機構名稱
    project_title TEXT NOT NULL,           -- 創新實驗專案名稱
    approval_date TEXT,                    -- 金管會核准開展實驗日
    status TEXT,                           -- 實驗狀態 (COMPLETED: 畢業出沙盒, IN_PROGRESS: 實驗中, TERMINATED: 終止)
    partner_bank TEXT,                     -- 協同合作金融機構
    core_innovation TEXT                   -- 核心金融科技技術要旨
);
```

### 表 17：`f60_ghg_emissions_timeseries` (35 年國家溫室氣體時序排放表)
```sql
CREATE TABLE IF NOT EXISTS f60_ghg_emissions_timeseries (
    year INTEGER PRIMARY KEY,              -- 統計年度 (1990 ~ 2024)
    total_net_emissions_mt REAL,           -- 總淨排放量 (百萬公噸 CO2e)
    energy_sector_emissions REAL,          -- 能源部門排放量
    industrial_processes_emissions REAL,   -- 工業製程部門排放量
    agriculture_emissions REAL,            -- 農業部門排放量
    waste_emissions REAL                   -- 廢棄物部門排放量
);
```
