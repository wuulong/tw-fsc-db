# 📋 F50: 法律事務、處分裁罰與評議爭議智庫規格書 (F50_SPECIFICATION.md)

* **模組代號**：`f50_sanctions_legal_db`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 法律事務處 / 金融消費評議中心
* **版本號**：`v1.0.0` (真實處分書 499 筆全量落地 + FTS5 違規事實檢索 + 評議爭議追蹤)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-007]` 全國法規與裁罰案件語意關聯規格
  * `[FSC-SPC-008]` 全域金融實體倒排搜尋與監理儀表板規格

---

## 1. 模組使命與四大業務情境 (Mission & Scenarios)

> 💡 **核心原則**：「拒絕空洞假資料，全面利用 499 筆真實金管會裁罰處分書與金融消費評議資料！」

### 核心情境一：全域金融重大裁罰處分實體庫 (`f50_sanctions`)
- **涵蓋範圍**：金管會針對銀行、金控、證券商、投信投顧、期貨商、保險業之正式重大行政裁處書。
- **資料特徵解構**：
  1. `doc_no`：主管機關正式發文字號 (如 `金管銀控字第11502721972號`)
  2. `sanction_date`：裁處發文日期 (標準化 ISO: `YYYY-MM-DD`)
  3. `target_name`：受處分金融機構全銜 (如 `合作金庫商業銀行股份有限公司`)
  4. `tax_id`：受處分機構 8 碼統一編號 (如 `70799128`)
  5. `penalty_fine_ntd`：裁處罰鍰金額 (新臺幣元，如 `12,000,000`)
  6. `main_subject`：處分主旨 (罰鍰、糾正、命令解除經理人職務、暫停業務)
  7. `violation_facts`：具體違法或違規情節事實
  8. `legal_basis`：處分適用之法令條號依據
  9. `agency_bureau`：處分業務局處 (銀行局、證期局、保險局)

### 核心情境二：違規事實法條 FTS5 全文倒排檢索 (`f50_sanctions_fts`)
- 採用 SQLite 原生 FTS5 倒排索引，針對處分發文字號、受處分機構、違法事實情節與處分主旨建立全文索引。
- 支援法遵、律師與金融稽核以違規行為（如「信用卡疑義帳款」、「洗錢防制審查」、「資安系統中斷」、「理專挪用款項」）秒級檢索歷史裁罰先例與裁量金額。

### 核心情境三：金融消費評議爭議申訴統計 (`f50_ombudsman_cases`)
- 記錄財團法人金融消費評議中心發布之銀行業及金融服務業歷季爭議申訴件數與爭議比率。
- 提供金融機構客訴風險與消費者權益保護指標。

### 核心情境四：機構累計裁罰與罰鍰排行榜檢視表 (`v_f50_institution_sanction_summary`)
- 自動按受處分機構進行分組，統計各金融機構歷史重大裁罰累計次數、累計罰鍰總金額與最新處分日期。
- 為 F00 監理雷達提供量化風控數值。

---

## 2. 核心資料庫模型規格 (`schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS f50_sanctions (
    sanction_uid TEXT PRIMARY KEY,        -- SNC_{doc_no_hash}
    doc_no TEXT NOT NULL,                 -- 主管機關發文字號
    sanction_date TEXT NOT NULL,          -- 處分日期 (ISO: YYYY-MM-DD)
    target_name TEXT NOT NULL,            -- 受處分人/機構全銜
    tax_id TEXT,                          -- 統一編號
    penalty_fine_ntd REAL DEFAULT 0.0,    -- 罰鍰金額 (新臺幣元)
    agency_bureau TEXT NOT NULL,          -- 業務局處
    main_subject TEXT NOT NULL,           -- 主旨
    violation_facts TEXT,                 -- 事實情節
    legal_basis TEXT,                     -- 法令依據
    source_url TEXT,                      -- 原處分書連結
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f50_date ON f50_sanctions(sanction_date);
CREATE INDEX IF NOT EXISTS idx_f50_target ON f50_sanctions(target_name);
CREATE INDEX IF NOT EXISTS idx_f50_tax ON f50_sanctions(tax_id);

CREATE VIRTUAL TABLE IF NOT EXISTS f50_sanctions_fts USING fts5(
    sanction_uid UNINDEXED,
    doc_no,
    target_name,
    main_subject,
    violation_facts,
    legal_basis,
    tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS f50_ombudsman_cases (
    case_uid TEXT PRIMARY KEY,            -- OMB_{period}_{bank_hash}
    start_date TEXT NOT NULL,             -- 統計起日 (ISO: YYYY-MM-DD)
    end_date TEXT NOT NULL,               -- 統計迄日 (ISO: YYYY-MM-DD)
    institution_name TEXT NOT NULL,       -- 爭議機構名稱
    complaint_count INTEGER NOT NULL,     -- 申訴件數
    complaint_ratio REAL,                 -- 案件比率 (%)
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_f50_omb_inst ON f50_ombudsman_cases(institution_name);

CREATE VIEW IF NOT EXISTS v_f50_institution_sanction_summary AS
SELECT 
    target_name,
    COUNT(*) AS total_sanctions_count,
    SUM(penalty_fine_ntd) AS total_penalty_fine_ntd,
    MAX(sanction_date) AS latest_sanction_date
FROM f50_sanctions
GROUP BY target_name
ORDER BY total_penalty_fine_ntd DESC;
```
