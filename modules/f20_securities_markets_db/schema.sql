-- ==============================================================================
-- 🏛️ F20: 證券期貨與公開市場模組 Schema (f20_securities_markets_db)
-- 版本: v1.0.0 (證期雙輪全覆蓋 + 地面真值齊備 + SQLite 原生 UDF 全面下沉)
-- ==============================================================================

-- 1. 公開發行公司基準主表
CREATE TABLE IF NOT EXISTS f20_companies (
    company_code TEXT PRIMARY KEY,         -- 股票/公司代號 (如 1101, 2330)
    company_name TEXT NOT NULL,            -- 公司簡稱 (如 台泥, 台積電)
    isin_code TEXT UNIQUE,                 -- 國際證券辨識碼 (如 TW0001101004)
    listing_date TEXT NOT NULL,            -- 上市/掛牌日期 (ISO-8601: YYYY-MM-DD)
    market_type TEXT NOT NULL,             -- 市場別 (上市, 上櫃, 興櫃, 公開發行)
    industry_category TEXT NOT NULL,       -- 產業類別 (如 水泥工業, 半導體業)
    cfi_code TEXT,                         -- 財務工具分類碼 (CFI Code)
    updated_at TEXT NOT NULL,              -- ISO-8601 時間戳
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_comp_industry ON f20_companies(industry_category);
CREATE INDEX IF NOT EXISTS idx_f20_comp_market ON f20_companies(market_type);

-- 2. 每月營業收入彙總表
CREATE TABLE IF NOT EXISTS f20_monthly_revenues (
    revenue_uid TEXT PRIMARY KEY,          -- 主碼: REV_[年月]_[公司代號]
    company_code TEXT NOT NULL,            -- 股票代號 (外鍵連至 f20_companies)
    company_name TEXT NOT NULL,            -- 申報公司名稱
    industry_name TEXT,                    -- 申報產業別
    revenue_year_month TEXT NOT NULL,      -- 營收年月 (ISO: YYYY-MM)
    report_date TEXT NOT NULL,             -- 出表日期 (ISO: YYYY-MM-DD)
    current_month_revenue REAL,            -- 當月營業收入 (千元)
    last_month_revenue REAL,               -- 上月營業收入 (千元)
    last_year_same_month_revenue REAL,     -- 去年同月營業收入 (千元)
    mom_growth_rate REAL,                  -- 上月比較增減率 (%)
    yoy_growth_rate REAL,                  -- 去年同月比較增減率 (%)
    cum_current_revenue REAL,              -- 當年累計營收 (千元)
    cum_last_year_revenue REAL,            -- 去年累計營收 (千元)
    cum_yoy_growth_rate REAL,              -- 前期比較增減率 (%)
    note TEXT,                             -- 備註說明
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_rev_ym ON f20_monthly_revenues(revenue_year_month);
CREATE INDEX IF NOT EXISTS idx_f20_rev_yoy ON f20_monthly_revenues(yoy_growth_rate);

-- 3. 上市公司 10% 大股東申報表
CREATE TABLE IF NOT EXISTS f20_major_shareholders (
    shareholder_uid TEXT PRIMARY KEY,      -- 主碼: SH_[公司代號]_[大股東名稱HASH]
    company_code TEXT NOT NULL,            -- 股票代號
    company_name TEXT NOT NULL,            -- 公司名稱
    shareholder_name TEXT NOT NULL,        -- 大股東姓名/法人全銜
    report_date TEXT NOT NULL,             -- 申報/基準出表日 (ISO: YYYY-MM-DD)
    is_corporate INTEGER DEFAULT 0,        -- 0: 自然人, 1: 法人機構
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_sh_code ON f20_major_shareholders(company_code);
CREATE INDEX IF NOT EXISTS idx_f20_sh_name ON f20_major_shareholders(shareholder_name);

-- 4. 股票市場估值與投資價值指標表 (f20_market_valuations)
CREATE TABLE IF NOT EXISTS f20_market_valuations (
    valuation_uid TEXT PRIMARY KEY,        -- 主碼: VAL_[日期]_[股票代號]
    company_code TEXT NOT NULL,            -- 股票代號
    company_name TEXT NOT NULL,            -- 公司簡稱
    pe_ratio REAL,                         -- 本益比 (P/E Ratio)
    dividend_yield REAL,                   -- 殖利率 (%) (Dividend Yield)
    pb_ratio REAL,                         -- 股價淨值比 (P/B Ratio)
    dividend_per_share REAL,               -- 每股股利 (元)
    dividend_year TEXT,                    -- 股利所屬年度
    report_quarter TEXT,                   -- 財報基準年/季 (如 115Q2)
    trade_date TEXT NOT NULL,              -- 交易日期 (ISO: YYYY-MM-DD)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_val_pe ON f20_market_valuations(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_f20_val_yield ON f20_market_valuations(dividend_yield);

-- 5. 臺灣期貨交易所商品交易量與未平倉表 (f20_futures_trading)
CREATE TABLE IF NOT EXISTS f20_futures_trading (
    contract_code TEXT PRIMARY KEY,        -- 契約代號 (如 TX, MTX, TE, TF)
    contract_name TEXT NOT NULL,           -- 契約名稱 (如 臺股期貨, 小型臺指期貨)
    trade_month TEXT NOT NULL,             -- 交易年月 (ISO: YYYY-MM)
    total_volume INTEGER,                  -- 月總成交量 (口)
    daily_avg_volume INTEGER,              -- 日均成交量 (口)
    open_interest INTEGER,                 -- 未平倉合約口數 (口)
    contract_value_million REAL,           -- 契約總價值 (百萬元)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_fut_vol ON f20_futures_trading(total_volume);

-- 6. 模組內部跨表整合檢視表: 公司全維度價值成長 Profile
CREATE VIEW IF NOT EXISTS v_f20_company_revenue_profile AS
SELECT 
    c.company_code,
    c.company_name,
    c.market_type,
    c.industry_category,
    c.listing_date,
    r.revenue_year_month,
    r.current_month_revenue,
    r.mom_growth_rate,
    r.yoy_growth_rate,
    r.cum_yoy_growth_rate,
    v.pe_ratio,
    v.dividend_yield,
    v.pb_ratio,
    COUNT(DISTINCT s.shareholder_name) AS major_shareholders_count,
    GROUP_CONCAT(DISTINCT s.shareholder_name) AS major_shareholders_summary
FROM f20_companies c
LEFT JOIN f20_monthly_revenues r ON c.company_code = r.company_code
LEFT JOIN f20_market_valuations v ON c.company_code = v.company_code
LEFT JOIN f20_major_shareholders s ON c.company_code = s.company_code
GROUP BY c.company_code, r.revenue_year_month;

-- 7. 跨模組集團連動檢視表 (F20 ↔ F10 金控上市集團控制力)
CREATE VIEW IF NOT EXISTS v_f20_f10_financial_group_synergy AS
SELECT 
    c.company_code,
    c.company_name,
    h.holding_name,
    h.group_assets_billion,
    r.revenue_year_month,
    r.current_month_revenue,
    r.yoy_growth_rate,
    v.pe_ratio,
    v.dividend_yield
FROM f20_companies c
JOIN f10_financial_holdings h ON (h.holding_name LIKE '%' || c.company_name || '%' OR h.subsidiaries_text LIKE '%' || c.company_name || '%')
LEFT JOIN f20_monthly_revenues r ON c.company_code = r.company_code
LEFT JOIN f20_market_valuations v ON c.company_code = v.company_code;
