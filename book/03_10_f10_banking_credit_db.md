# 📘 3.10 F10 銀行機構、信用金融與消費金融智庫 (03_10_f10_banking_credit_db.md)

* **模組代號**：`f10_banking_credit_db`
* **所屬機關**：金融監督管理委員會 (GOV-A21) 銀行局
* **受控版本**：`v1.0.0`
* **對應規格**：[F10_SPECIFICATION.md](../modules/f10_banking_credit_db/F10_SPECIFICATION.md) | [F10_ADVANCED_SPEC.md](../modules/f10_banking_credit_db/F10_ADVANCED_SPEC.md)
* **實測驗證**：[test_f10.py](../modules/f10_banking_credit_db/tests/test_f10.py) (5/5 綠燈 PASS)

---

## 1. 業務情境與解決的金融痛點 (Domain Purpose & Pain Points)

銀行業是國家整體經濟的資金心臟，管理超過 60 兆元新台幣的國民存款與企業貸款。然而，在日常金融監理、企金授信與民眾消費決策中，長期存在著三大現實痛點：

1. **不動產授信暴險的「隱形臨界點」**：
   依據《銀行法》第 72 條之 2，商業銀行建築放款不得超過放款時存款與金融債券總合的 30%。但過去各銀行的土地擔保放款餘額與集中度散落於不同季報中，央行與金管會每次要排查「哪些銀行快踩到 28.5% 警戒紅線」，都必須由稽核人員耗費數週人工索取與計算，無法即時進行動態監控。
2. **信用卡發卡「虛胖數字」與真實動能割裂**：
   發卡銀行常對外宣傳發卡量突破數百萬張，但大量卡片在發行後便淪為「呆卡」。主管機關與市場分析師若只看流通卡數，完全無法掌握真正的消費動能與信用風險（例如循環信用餘額與逾期三個月以上帳款的消長）。
3. **金控集團跨子公司授信的「左右手盲區」**：
   金控母公司名下擁有銀行、證券、壽險等多家子公司，但各子公司的資產品質、放款逾放比（NPL）與備抵呆帳涵蓋率各自獨立揭露，缺乏一個整合檢視能一秒透視金控集團底下的銀行實質經營體質。

`F10 銀行機構、信用金融與消費金融智庫` 的核心使命，就是透過**結構化五大真實資料集**與**下沉 SQLite 引擎指標**，將全台銀行、金控、土地放款與信用卡消費資料打造成一套可即時排查、自動分級警戒的實戰知識庫。

---

## 2. 官方開放資料源與金管會權責局處 (Data Governance & Sources)

本模組 100% 採用金管會銀行局與財團法人金融聯合徵信中心之官方真實資料：

| 資料集編號 | 資料集名稱 | 主管權責機關 | 本機真實範例檔案連結 | 官方下載端點 (URL) |
| :--- | :--- | :--- | :--- | :--- |
| **`10689`** | 金融控股公司設立情形表 | 金管會銀行局 | [`f10_fhc_setup_sample.csv`](../data/samples/f10_fhc_setup_sample.csv) | `https://www.banking.gov.tw/.../banking20.csv` |
| **`10525`** | 本國銀行營運與資產品質表 (Banking12) | 金管會銀行局 | [`f10_banking12_sample.csv`](../data/samples/f10_banking12_sample.csv) | `https://www.banking.gov.tw/.../banking12.csv` |
| **`26053`** | 以土地為擔保品之放款餘額與集中度 | 金管會銀行局 | [`f10_land_loan_sample.csv`](../data/samples/f10_land_loan_sample.csv) | `https://www.banking.gov.tw/.../banking09.csv` |
| **`10528`** | 信用卡重要業務及財務資訊表 | 金管會銀行局 | [`f10_credit_card_sample.csv`](../data/samples/f10_credit_card_sample.csv) | `https://www.banking.gov.tw/.../banking13.csv` |
| **`SEED-CORP`** | 聯徵中心全台企業總貸款統計趨勢 | 財團法人金融聯合徵信中心 | [`f10_corporate_loan_sample.csv`](../data/samples/f10_corporate_loan_sample.csv) | `data/raw/f10_corporate_loan_trends.csv` |


---

## 3. 跨模組對接拓樸與資料流向 (Fig 3.10)

F10 絕非封閉的單點資料表，它居中扮演金控母公司與下游實體業務的「樞紐連接器」：

```mermaid
graph TD
    subgraph F00_Master["🧠 F00 母大腦中樞"]
        REG["🏛️ 全域實體名冊 (f00_entity_registry)"]
        V360["👁️ 360° 監理檔案檢視 (v_f00_entity_360_profile)"]
    end

    subgraph F10["🏦 F10 銀行與信用金融智庫"]
        FHC["f10_financial_holdings<br/>(金控設立與規模)"]
        BANK["f10_bank_asset_quality<br/>(放款/逾放比/呆帳)"]
        LAND["f10_land_collateral_loans<br/>(土地融資與72-2比率)"]
        CARD["f10_credit_card_operations<br/>(簽帳/活卡率/循環信用)"]
        CORP["f10_corporate_loan_trends<br/>(全台企貸總體時序)"]
    end

    subgraph CrossLink["🔗 跨模組下游穿透聯動"]
        F50["⚖️ F50 法律裁罰智庫<br/>(重大處分案由 & 罰鍰)"]
        F60["🚀 F60 科技與永續智庫<br/>(VASP 法幣代管信託銀行)"]
    end

    %% 關聯
    FHC -->|子公司映射| BANK
    BANK -->|實體主鍵 (統編/名稱)| LAND
    BANK -->|機構名稱勾稽| CARD
    
    BANK -->|銀行實體與資產指標| REG
    FHC -->|金控實體與資產規模| REG
    
    BANK --> V360
    LAND --> V360
    CARD --> V360

    BANK -.->|勾稽歷史裁罰| F50
    BANK -.->|擔任代管信託帳戶| F60

    classDef f00Style fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef f10Style fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1.5px;
    classDef linkStyle fill:#fff3e0,stroke:#f57c00,stroke-width:1.5px;

    class F00_Master f00Style;
    class F10 f10Style;
    class CrossLink linkStyle;
```
*Fig 3.10: F10 與 F00 母大腦、F50 裁罰、F60 沙盒之關聯與資料流向圖*

---

## 4. SQLite 資料庫 Schema 與資料模型 (Data Model & Schema)

F10 模組建立了 5 大實體表與 2 大業務檢視，全面採用 `INSERT OR REPLACE INTO` 確保補充式無縫演進：

### 4.1 核心實體表 DDL

```sql
-- 1. 金融控股公司及子公司明細表
CREATE TABLE IF NOT EXISTS f10_financial_holdings (
    holding_name TEXT PRIMARY KEY,        -- 金控公司名稱 (如 富邦金融控股股份有限公司)
    approved_date TEXT,                   -- 核准設立日期 (ISO 8601: YYYY-MM-DD)
    opening_date TEXT,                    -- 開業日期 (ISO 8601: YYYY-MM-DD)
    group_assets_billion REAL,            -- 集團資產 (單位: 10億元新臺幣)
    group_net_worth_billion REAL,         -- 集團淨值 (單位: 10億元新臺幣)
    subsidiaries_text TEXT,               -- 子公司清單字串 (如 銀行、人壽、產險、證券)
    subsidiaries_count INTEGER,           -- 子公司數量統計 (UDF COUNT_DELIMITED)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

-- 2. 土地擔保放款餘額與集中度表 (銀行法 72-2 條監控)
CREATE TABLE IF NOT EXISTS f10_land_collateral_loans (
    bank_name TEXT PRIMARY KEY,           -- 金融機構名稱
    land_loan_balance REAL,               -- 以土地為擔保品之放款餘額 (百萬元)
    total_loan_including_call REAL,       -- 放款總額含催收款 (百萬元)
    land_loan_ratio REAL,                 -- 土地放款佔放款總額比率 (%) (UDF BANK_72_2_RATIO)
    updated_at TEXT NOT NULL              -- ISO-8601 時間戳
);

-- 3. 信用卡重要業務及財務資訊表 (消費金融動態)
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
```

### 4.2 跨表聚合檢視：金控與銀行全景總覽 (`v_f10_holding_banking_summary`)
透過跨表檢視，金控資產規模、放款逾放比、土地融資集中度與信用卡活卡率瞬間聚合：

```sql
CREATE VIEW IF NOT EXISTS v_f10_holding_banking_summary AS
SELECT 
    h.holding_name,
    h.group_assets_billion,
    h.subsidiaries_count,
    b.bank_name,
    b.deposit_amount,
    b.loan_total,
    b.npl_ratio,
    l.land_loan_ratio,
    c.signing_amount_million AS cc_signing_amount,
    c.active_card_ratio AS cc_active_ratio
FROM f10_financial_holdings h
LEFT JOIN f10_bank_asset_quality b ON h.subsidiaries_text LIKE '%' || b.bank_name || '%'
LEFT JOIN f10_land_collateral_loans l ON b.bank_name = l.bank_name
LEFT JOIN f10_credit_card_operations c ON b.bank_name = c.institution_name;
```

### 4.3 地面真實資料展示 (Real Data Row)
```json
{
  "holding_name": "富邦金融控股股份有限公司",
  "bank_name": "台北富邦商業銀行",
  "deposit_amount": 3261450.0,
  "loan_total": 2410280.0,
  "npl_ratio": 0.12,
  "land_loan_ratio": 2.82,
  "cc_signing_amount": 53621.5,
  "cc_active_ratio": 64.21,
  "supervisory_risk_badge": "GREEN"
}
```

---

## 5. 核心監理指標計算與 SQLite UDF 實作 (Metrics & Rules)

本模組堅決杜絕 Python 重型迴圈，所有指標全面由 SQLite 原生 UDF 秒級完成計算：

### 1. 土地擔保放款警戒比率 (`BANK_72_2_RATIO`)
* **計算公式**：
  $$\text{土地融資比率} (\%) = \frac{\text{土地擔保放款餘額}}{\text{放款總額含催收款}} \times 100\%$$
* **防呆處理**：UDF 內建除以零保護，若分母為零或空值自動回傳 `0.0`。

### 2. 信用卡真實活卡率 (Active Card Ratio)
* **計算公式**：
  $$\text{活卡率} (\%) = \frac{\text{有效卡數}}{\text{流通卡數}} \times 100\%$$
* **業務意涵**：精確過濾各家銀行的呆卡包袱，識別哪家銀行真正具備強大的民間實質消費黏著度。

### 3. 資產品質監理燈號評定 (`RISK_BADGE`)
結合逾期放款比率（NPL Ratio）與備抵呆帳涵蓋率（Coverage Ratio），自動給予風險燈號：
* 🟢 **`GREEN` (體質健全)**：$\text{NPL} \le 0.20\%$ 且 $\text{涵蓋率} \ge 500\%$。
* 🟡 **`YELLOW` (密切觀察)**：$0.20\% < \text{NPL} \le 0.50\%$ 或 $\text{涵蓋率} < 500\%$。
* 🔴 **`RED` (監理警戒)**：$\text{NPL} > 0.50\%$。

---

## 6. 專屬 CLI 指令實戰與 JSON 管線輸出 (CLI Operations)

透過 `fsc_cli.py`（或根目錄 `just fsc-bank`），讀者可在命令列中一秒進行以下業務查詢：

### 1. 查詢全台銀行名錄與資本實力
```bash
python src/cli/fsc_cli.py bank list --limit 5
```
*(終端美化輸出銀行程式碼、存款總額、放款總額與逾放比率)*

### 2. 查詢全台信用卡月簽帳排行與活卡率
```bash
python src/cli/fsc_cli.py bank credit-card --limit 5
```
*(輸出各大發卡銀行當月簽帳金額、循環信用餘額與活卡率排序)*

### 3. 排查土地融資高集中度機構
```bash
python src/cli/fsc_cli.py bank mortgage --limit 5
```
*(輸出以土地為擔保之放款餘額與佔比排行，即時辨識潛在暴險)*

### 4. 自動化管線 JSON 串接範例
```bash
python src/cli/fsc_cli.py bank credit-card -j | jq '.results[] | select(.active_card_ratio > 65)'
```

---

## 7. 地面真實資料物理指標與驗證證明 (Empirical Proof & PASS)

* **地面真實資料入庫規模**：
  - `f10_financial_holdings`：**14 筆** (全台 14 大金控集團)
  - `f10_bank_asset_quality`：**39 筆** (本國銀行與主要外商銀行)
  - `f10_land_collateral_loans`：**38 筆** (土地融資放款明細)
  - `f10_credit_card_operations`：**32 筆** (全台主要發卡金融機構)
  - `f10_corporate_loan_trends`：**48 筆** (聯徵中心全時序企貸趨勢)
  - **F10 模組總地面真值筆數**：**171 筆核心監理指標列**（完全零假資料）
* **單元測試驗證 (Unit Test Proof)**：
  - 測試腳本：`modules/f10_banking_credit_db/tests/test_f10.py`
  - 驗證案例：涵蓋 DDL 建立、UDF 算式、五大表 ETL、檢視聚合與極端值除零防呆。
  - 驗證成果：**`5/5 PASS` (100% 綠燈通過)**。
