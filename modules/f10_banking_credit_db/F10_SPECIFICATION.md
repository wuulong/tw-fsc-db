# 📋 F10: 銀行與信用金融模組基礎規格書 (F10_SPECIFICATION.md)

* **模組代號**：`f10_banking_credit_db`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 銀行局
* **版本號**：`v2.1.0` (五大地面真值齊備 + SQLite 原生 UDF 全面下沉)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-001]` 權威法人統編主鍵自動繫結規格
  * `[FSC-SPC-002]` 金融機構名錄與資產品質對照規格

---

## 1. 模組定位與本職責任 (Module Scope & Self-Contained Responsibilities)

`f10_banking_credit_db` 是金融監理體系中最厚實的基石，涵蓋全台灣金控集團體系、本國商業銀行、土地擔保融資、信用卡業務與聯徵全台企貸統計。**本模組自身必須獨立搞定的基本功能包括**：
1. **五大地面真值開放資料集之自包含清洗與入庫**：
   - 金融控股公司設立情形與子公司名冊 (`f10_fhc_setup_sample.csv`)。
   - 本國銀行資產品質、淨值、逾放比與呆帳涵蓋率 (`f10_banking12_sample.csv`)。
   - 以土地為擔保品之放款餘額與集中度 (`f10_land_loan_sample.csv`)。
   - 信用卡流通卡數、簽帳金額、循環信用與逾期款 (`f10_credit_card_sample.csv`)。
   - 聯徵中心全台灣企業總貸款統計趨勢 (`f10_corporate_loan_sample.csv`)。
2. **SQLite 原生 UDF 全面下沉運算 (零 Python 重型迴圈)**：
   - `COUNT_DELIMITED`：清洗子公司清單頓號並計算 `subsidiaries_count`。
   - `BANK_72_2_RATIO`：計算土地放款比率與信用卡活卡率，具備除以零安全防呆。
   - `RISK_BADGE`：結合逾放比與涵蓋率動態計算資產品質燈號 (`GREEN`, `YELLOW`, `RED`)。
3. **金控集團與跨表業務聯動檢視表**：
   - `v_f10_holding_banking_summary`：金控規模、銀行放款、逾放比與信用卡消費力聚合。
   - `v_f10_bank_credit_risk_profile`：銀行資產品質、土融比率、信用卡違約與監理燈號雷達。
4. **元資料治理自動化**：
   - 入庫完成後自動將各表紀錄筆數與時間戳註冊至 `sys_module_metadata`。

---

## 2. 基礎資料庫模型與 DDL 規格 (`schema.sql`)

### 2.1 金融控股公司及子公司明細表 (`f10_financial_holdings`)
```sql
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
```

### 2.2 本國銀行營運與資產品質表 (`f10_bank_asset_quality`)
```sql
CREATE TABLE IF NOT EXISTS f10_bank_asset_quality (
    bank_name TEXT PRIMARY KEY,           -- 銀行名稱 (如 臺灣銀行, 臺灣土地銀行)
    deposit_amount REAL,                  -- 存款總額 (百萬元)
    pretax_profit REAL,                   -- 稅前盈餘 (百萬元)
    loan_total REAL,                      -- 放款總額 (百萬元)
    overdue_loan_total REAL,              -- 逾期放款總額 (百萬元)
    allowance_bad_debt REAL,              -- 貼現及放款提列之備抵呆帳 (百萬元)
    net_worth REAL,                       -- 淨值 (百萬元)
    npl_ratio REAL,                       -- 逾放比率 (%)
    coverage_ratio REAL,                  -- 備抵呆帳涵蓋率: 備抵呆帳/逾期放款 (%)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);
CREATE INDEX IF NOT EXISTS idx_f10_npl ON f10_bank_asset_quality(npl_ratio);
CREATE INDEX IF NOT EXISTS idx_f10_coverage ON f10_bank_asset_quality(coverage_ratio);
```

### 2.3 土地擔保放款餘額與集中度表 (`f10_land_collateral_loans`)
```sql
CREATE TABLE IF NOT EXISTS f10_land_collateral_loans (
    bank_name TEXT PRIMARY KEY,           -- 金融機構名稱
    land_loan_balance REAL,               -- 以土地為擔保品之放款餘額 (百萬元)
    total_loan_including_call REAL,       -- 放款總額含催收款 (百萬元)
    land_loan_ratio REAL,                 -- 土地放款佔放款總額比率 (%) (UDF BANK_72_2_RATIO)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);
CREATE INDEX IF NOT EXISTS idx_f10_land_loan_ratio ON f10_land_collateral_loans(land_loan_ratio);
```

### 2.4 信用卡業務與財務資訊表 (`f10_credit_card_operations`)
```sql
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
    active_card_ratio REAL,               -- 活卡率 (%) (UDF BANK_72_2_RATIO)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);
CREATE INDEX IF NOT EXISTS idx_f10_cc_signing ON f10_credit_card_operations(signing_amount_million);
CREATE INDEX IF NOT EXISTS idx_f10_cc_active_ratio ON f10_credit_card_operations(active_card_ratio);
```

### 2.5 聯徵中心全台企業貸款趨勢表 (`f10_corporate_loan_trends`)
```sql
CREATE TABLE IF NOT EXISTS f10_corporate_loan_trends (
    year_month TEXT PRIMARY KEY,          -- 年月份 (ISO: YYYY-MM)
    loan_entity_count INTEGER,            -- 企業貸款總家數
    loan_total_thousand REAL,             -- 企業貸款總金額 (仟元)
    loan_avg_thousand REAL,               -- 企業貸款平均金額 (仟元)
    loan_total_billion REAL,              -- 企業貸款總金額 (換算十億元)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);
CREATE INDEX IF NOT EXISTS idx_f10_corp_year_month ON f10_corporate_loan_trends(year_month);
```

### 2.6 跨表彙整檢視表 (`v_f10_holding_banking_summary` & `v_f10_bank_credit_risk_profile`)
```sql
-- 金控與旗下銀行總覽
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
LEFT JOIN f10_bank_asset_quality b ON h.subsidiaries_text LIKE '%' || b.bank_name || '%'
LEFT JOIN f10_land_collateral_loans l ON b.bank_name = l.bank_name
LEFT JOIN f10_credit_card_operations c ON b.bank_name = c.institution_name;

-- 銀行信用風險監理綜合指標檢視表 (UDF RISK_BADGE 燈號)
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
```

---

## 3. 基礎 CLI 與 Python API 介面規格

* **核心 API 函式 (`commands_f10.py`)**：
  * `run_f10_etl(db_path, fhc_sample, banking_sample, land_sample, credit_sample, corporate_sample) -> Dict[str, Any]`：執行全量 5 表入庫。
  * `query_financial_holdings(db_path, limit, min_assets) -> List[Dict[str, Any]]`：查詢金控。
  * `query_bank_asset_quality(db_path, limit, max_npl) -> List[Dict[str, Any]]`：查詢資產品質。
  * `query_land_collateral_loans(db_path, limit, min_ratio) -> List[Dict[str, Any]]`：查詢土地放款集中度。
  * `query_credit_card_operations(db_path, limit) -> List[Dict[str, Any]]`：查詢信用卡發卡與簽帳營運。
  * `query_corporate_loan_trends(db_path, limit) -> List[Dict[str, Any]]`：查詢全台企業總貸款月度趨勢。
  * `query_bank_credit_risk_radar(db_path, limit) -> List[Dict[str, Any]]`：查詢銀行信用風險綜合監理雷達。
  * `query_holding_banking_summary(db_path, limit) -> List[Dict[str, Any]]`：集團關聯檢視。
* **CLI 指令**：
  * `just fsc-bank holdings`：金控總資產榜。
  * `just fsc-bank quality`：本國銀行逾放比榜。
  * `just fsc-bank summary`：集團關聯檢視。