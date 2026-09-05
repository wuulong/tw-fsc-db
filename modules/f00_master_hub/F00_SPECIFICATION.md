# 📋 F00: 金管會母大腦全域倒排與元資料治理規格書 (F00_SPECIFICATION.md)

* **模組代號**：`f00_master_hub`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 資訊服務處 / 綜合規劃處
* **版本號**：`v1.0.0` (全域六大業務倒排全整合對接 + 360° 全景六維風控與虛實跨界治理)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-001]` 權威法人統編主鍵自動繫結規格
  * `[FSC-SPC-007]` 金融科技創新、VASP 與永續金融管線規格
  * `[FSC-SPC-008]` 全域金融實體倒排搜尋與監理儀表板規格

---

## 1. 模組定位與中樞整合職責 (Module Scope & Master Hub Responsibilities)

> 💡 **核心原則**：「功能不足，效能有什麼用！」
> `f00_master_hub` 絕不僅僅是一個單純執行 FTS 全文檢索的程式庫。身為整個金管會資料庫的母大腦，它必須**主動建立自身實體資料表，具體承載並解決各子模組 (F10~F60) 跨業務整合所需的實體消歧義、集團股權網路、與跨域風險聚合**。

### F00 必須自身搞定的 5 大實體整合業務情境：
1. **全域權威實體主檔案註冊庫 (`f00_entity_registry`)**：
   - 跨模組統整「金控 (F10)、本國銀行 (F10)、上市櫃公司 (F20)、保險公司 (F30)、受檢機構 (F40)、重大裁罰主體 (F50)、虛擬資產平台 VASP (F60)、金融科技沙盒新創 (F60)」。
   - 解決跨業務的主鍵映射：`8碼統編 (tax_id)` ↔ `4碼股票程式碼 (stock_code)` ↔ `金融機構程式碼 (banking_code)` ↔ `VASP登記碼 (vasp_reg_no)` ↔ `權威法定全銜 (canonical_name)` ↔ `常見商業別名 (common_alias)`。
2. **跨模組集團股權與控制力拓樸關連線 (`f00_entity_relations`)**：
   - 儲存金控母公司、上市子企業、未上市持股公司、海外轉投資事業的層級控制鏈。
   - 解決跨模組集團股權穿透：如富邦金控 (F10) ➔ 台北富邦商業銀行 (F10) ➔ 富邦證券 (F20) ➔ 富邦產險 (F30)。
3. **全域六維監理風險雷達與動態計分 (`f00_supervisory_radar`)**：
   - 整合六大維度：`F10 (銀行逾放比)` + `F20 (營收異常波幅)` + `F30/F50 (消費評議爭議)` + `F40 (金檢重大缺失)` + `F50 (歷史重大裁罰金額)` + `F60 (虛擬資產洗防監控/ESG 碳排暴險)`。
   - 計算單一機構之全域綜合監理風險指標與紅黃綠動態燈號（🟢 穩健 / 🟡 關注 / 🔴 警戒）。
4. **全域六域 FTS5 倒排索引 (`fts_fsc_global`)**：
   - 完整涵蓋：
     - `F10`: 金融控股公司、本國商業銀行、轉投資關係企業
     - `F20`: 上市公司、上櫃股票估值
     - `F30`: 產壽險機構、精算專業配置
     - `F40`: 金融檢查重大缺失態樣、情節與改善作法 (INSPECTION)
     - `F50`: 重大行政處分裁罰書字號、主旨、事實與法條 (SANCTION)
     - `F60`: 虛擬資產平台業者名冊 (VASP)、金融科技沙盒創新實驗專案 (SANDBOX)
   - 支援全專案一鍵全文檢索，雙軌 fallback 至 LIKE 模糊檢索。
5. **360° 跨模組全景實體檢視表 (`v_f00_entity_360_profile`)**：
   - 一鍵橫向穿透調閱機構全貌檔案：金控資產、銀行放款、逾放比、信用卡月簽帳、上市公司月營收、保險精算人力、評議中心爭議申訴、金檢缺失次數、歷史處分罰鍰、VASP 信託代管銀行與沙盒實驗成果。

---

## 2. 核心資料庫模型與 DDL 規格 (`schema.sql`)

### 2.1 全域金融法人實體權威登記主表 (`f00_entity_registry`)
```sql
CREATE TABLE IF NOT EXISTS f00_entity_registry (
    master_uid TEXT PRIMARY KEY,          -- ENT_{tax_id} 或 ENT_{stock_code}
    tax_id TEXT UNIQUE,                   -- 財政部 8 碼營利事業統一編號
    stock_code TEXT UNIQUE,               -- 證券公開發行 4 碼股票代號 (F20)
    banking_code TEXT,                    -- 銀行機構金融程式碼 (F10)
    insurance_code TEXT,                  -- 保險機構程式碼 (F30)
    vasp_reg_no TEXT,                     -- 虛擬資產洗錢防制聲明登記代號 (F60)
    canonical_name TEXT NOT NULL,         -- 權威法定全銜
    common_alias TEXT,                    -- 商業簡稱與交易品牌
    entity_class TEXT NOT NULL,           -- FHC, BANK, SECURITIES, INSURER, LISTED, VASP, FINTECH_SANDBOX
    is_financial_institution INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f00_ent_tax ON f00_entity_registry(tax_id);
CREATE INDEX IF NOT EXISTS idx_f00_ent_stock ON f00_entity_registry(stock_code);
CREATE INDEX IF NOT EXISTS idx_f00_ent_class ON f00_entity_registry(entity_class);
```
