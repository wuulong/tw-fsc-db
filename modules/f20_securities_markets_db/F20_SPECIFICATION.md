# 📋 F20: 證券期貨與公開市場模組基礎規格書 (F20_SPECIFICATION.md)

* **模組代號**：`f20_securities_markets_db`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 證券期貨局 / 證交所 / 櫃買中心 / 期交所
* **版本號**：`v1.0.0` (粗粒度業務聚合架構)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-001]` 權威法人統編主鍵自動繫結規格
  * `[FSC-SPC-003]` 證券期貨公開市場聚合管線規格

---

## 1. 模組定位與業務本位原則 (Module Scope & Business-First Principles)

> 💡 **核心原則**：「功能不足，效能有什麼用！」
> 本模組不只是上市櫃股票代號的儲存庫，其核心在於提供資本市場深度的**公開資訊觀測、成長動能監測、股權治理結構穿透與異常交易預警**。本規格書必須完整落實子業務模組的 **4 大實戰業務情境**。

---

## 2. 四大實戰業務情境規格發想 (Four Real-World Business Scenarios)

### 2.1 權威實體主檔案與別名消歧義 (Entity Master Profile & Disambiguation)
* **業務情境**：
  - 台灣公開市場包含上市、上櫃、興櫃與公開發行等多重板塊。
  - 公司更名（如中華開發 ➔ 凱基金控）、股票代號變更或別名（如台泥 vs 臺灣水泥股份有限公司）在市場上普遍存在。
* **業務模型規格**：
  - `f20_companies` 整合國際證券辨識碼 (ISIN)、4 碼股票代號、CFI 財務工具分類碼與上市日期。
  - 主鍵固定為 4 碼股票代號 (`company_code`)，輔以 `isin_code` 唯一約束，排除 ETF/ETN/TDR 等非普通股，建立資本市場基準主檔案。

### 2.2 領域核心指標計算與衍生特徵 (Domain Metrics & Feature Derivation)
* **業務情境**：
  - 單純的「當月營收數字」對投資人與監理機關毫無意義，必須從月營收申報資料中即時計算出專業衍生指標。
* **指標計算規格**：
  1. **營收成長動能指標**：
     - 月增率 (MoM %): `(當月營收 - 上月營收) / 上月營收 * 100`。
     - 年增率 (YoY %): `(當月營收 - 去年同月營收) / 去年同月營收 * 100`。
     - 累計年增率 (Cum YoY %): `(當年累計 - 去年同期累計) / 去年同期累計 * 100`。
  2. **股權籌碼集中度指標**：
     - 10% 外部大股東人數 (`major_shareholders_count`)。
     - 大股東法人持股佔比 (`corporate_shareholder_ratio`)。

### 2.3 異常檢測、臨界值預警與稽核規則 (Anomaly Alerts & Rules)
* **業務情境**：
  - 證券商與公開發行公司可能因金融資產評價損失出現負營收；或營收出現斷崖式暴跌或暴增，需自動發出監理紅黃燈。
* **稽核規格**：
  1. **負營收異常標記**：
     - 負數營收數值（如亞東證券 `-113,394` 千元）精確存入 `current_month_revenue`，不得被歸零。
     - 在 `attributes_json` 自動打上 `{"is_negative_revenue": true}` 標記。
  2. **營收劇烈波動預警燈號**：
     - 🔴 **警戒**：當月營收 YoY 跌幅超過 `-50%` 或增幅超過 `+200%`（疑似借殼、重大停工或業務劇變）。
     - 🟡 **關注**：連續三個月營收 YoY 呈現衰退。
     - 🟢 **穩健**：營收穩健成長（YoY 介於 `0% ~ +30%`）。
  3. **大股東法人/自然人去重雜湊防重**：
     - 大股東主鍵採用決定性 MD5 雜湊：`SH_{company_code}_{MD5(shareholder_name)[:8]}`，避免重名衝突或字串覆寫。

### 2.4 複合式聚合檢視表與領域洞察檢視 (Analytical Views)
* **業務情境**：
  - 主管機關或分析師需要一眼綜覽「公司基本面 + 成長動能 + 董監大股東」。
* **檢視表規格 (`v_f20_company_revenue_profile`)**：
  ```sql
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
      COUNT(DISTINCT s.shareholder_name) AS major_shareholders_count,
      GROUP_CONCAT(s.shareholder_name, '、') AS major_shareholders_summary
  FROM f20_companies c
  LEFT JOIN f20_monthly_revenues r ON c.company_code = r.company_code
  LEFT JOIN f20_major_shareholders s ON c.company_code = s.company_code
  GROUP BY c.company_code, r.revenue_year_month;
  ```

---

## 3. 基礎資料庫模型與 DDL 規格 (`schema.sql`)

### 3.1 公開發行公司基準主表 (`f20_companies`)
```sql
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
```

### 3.2 每月營業收入彙總表 (`f20_monthly_revenues`)
```sql
CREATE TABLE IF NOT EXISTS f20_monthly_revenues (
    revenue_uid TEXT PRIMARY KEY,          -- 主碼: REV_[年月]_[公司代號] (如 REV_202607_1101)
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
```

### 3.3 上市公司 10% 大股東申報表 (`f20_major_shareholders`)
```sql
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
```

### 3.4 股票市場估值與投資價值指標表 (`f20_market_valuations`)
```sql
CREATE TABLE IF NOT EXISTS f20_market_valuations (
    valuation_uid TEXT PRIMARY KEY,        -- 主碼: VAL_[日期]_[股票代號]
    company_code TEXT NOT NULL,            -- 股票代號
    company_name TEXT NOT NULL,            -- 公司簡稱
    pe_ratio REAL,                         -- 本益比 (P/E Ratio)
    dividend_yield REAL,                   -- 殖利率 (%) (Dividend Yield)
    pb_ratio REAL,                         -- 股價淨值比 (P/B Ratio)
    dividend_per_share REAL,               -- 每股股利 (元)
    dividend_year TEXT,                    -- 股利所屬年度
    report_quarter TEXT,                   -- 財報基準年/季
    trade_date TEXT NOT NULL,              -- 交易日期 (ISO: YYYY-MM-DD)
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f20_val_pe ON f20_market_valuations(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_f20_val_yield ON f20_market_valuations(dividend_yield);
```

### 3.5 臺灣期貨交易所商品交易量與未平倉表 (`f20_futures_trading`)
```sql
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
```

---

## 4. 基礎 CLI 與 Python API 介面規格

* **核心 API 函式 (`commands_f20.py`)**：
  * `run_f20_etl(...) -> Dict[str, Any]`：執行全量 5 大表入庫。
  * `query_top_revenue_companies(db_path, limit, min_yoy) -> List[Dict[str, Any]]`：查詢營收與年增率最高公司。
  * `query_company_profile(db_path, query_term) -> Optional[Dict[str, Any]]`：取得公司全維度營收、估值與大股東整合 Profile。
  * `query_major_shareholders(db_path, query_term) -> List[Dict[str, Any]]`：查詢 10% 大股東名單。
  * `query_market_valuations(db_path, limit, min_yield, max_pe) -> List[Dict[str, Any]]`：查詢高殖利率與本益比排行。
  * `query_futures_trading(db_path, limit) -> List[Dict[str, Any]]`：查詢期交所主力商品交易量與未平倉。
* **CLI 指令**：
  * `just fsc-comp-top` / `fsc company top`：營收排行與年增率。
  * `just fsc-comp-prof` / `fsc company profile <代號>`：公司全景 Profile。
  * `just fsc-comp-val` / `fsc company valuation`：股票市場估值與高殖利率排行。
  * `just fsc-comp-fut` / `fsc company futures`：期交所主力商品交易排行。
