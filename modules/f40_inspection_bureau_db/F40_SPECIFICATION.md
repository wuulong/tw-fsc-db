# 📋 F40: 金融檢查與重大缺失智庫規格書 (F40_SPECIFICATION.md)

* **模組代號**：`f40_inspection_bureau_db`
* **所屬部會**：金融監督管理委員會 (GOV-A21) 檢查局
* **版本號**：`v2.1.0` (業務本位深度發想 + 金檢四大業務情境 + 地面真值全面落地)
* **上位系統工程規格追溯**：
  * `[FSC-SPC-004]` 金融檢查與內控缺失自動歸納規格
  * `[FSC-SPC-008]` 全域金融實體倒排搜尋與監理儀表板規格

---

## 1. 模組定位與金融監理核心使命 (Module Scope & Core Mission)

> 💡 **核心原則**：「拒絕空洞抽象與玩具程式碼，全面落實業務功能本位！」
> 金管會檢查局是台灣特許金融體系的「獨立審計與紀律防線」。其職責不是單純收集罰單，而是**透過常態一般檢查、專案檢查與受託檢查，深入金融機構之內部控制、風險管理、公司治理與法規遵循防線，及早揪出系統性破口與潛在流動性/營運風險**。

本模組以金管會檢查局發布之歷年實地金融檢查「主要檢查缺失」與「實地檢查年度執行統計」為地面真值核心，自身必須獨立搞定的 4 大實戰業務情境：

### 核心情境一：全域金融檢查重大缺失實體庫 (`f40_exam_deficiencies`)
- **涵蓋對象**：金控集團 (`HOLDING`，66 筆) 與外國銀行在臺分行 (`FOREIGN_BANK`，34 筆)。
- **微觀缺失解構**：
  1. `eval_year` & `half_year`：年度與半年度時間軸（民國轉 ISO 標準化）。
  2. `business_category`：業務專案維度（內部管理、子公司管理、公司治理、風險管理、防制洗錢/資恐、授信業務、衍生性金融商品、資訊安全、個人資料保護等 10 大專案）。
  3. `deficiency_pattern`：缺失態樣核心標題（如「辦理餘屋貸款徵信審查欠嚴謹」、「未依規定將內稽查核報告交付審計委員會」）。
  4. `deficiency_detail`：缺失具體情節與違規實況（包含交易室門禁違規、高風險客戶持續審查缺失、AMC 不動產處分停滯、租賃融資規避選擇性信用管制等實戰案例）。
  5. `improvement_action`：檢查局明確具體之糾正作為與遵循法規函令（直接明載金管銀法字號、內控制度實施辦法條號）。

### 核心情境二：法遵缺失語意穿透全文倒排檢索 (`f40_deficiencies_fts`)
- 採用 SQLite 原生 FTS5 倒排索引（`tokenize='unicode61'`），針對缺失態樣、情節與改善作法進行全文索引。
- 支援金管會長官、檢查稽核員、受檢機構法遵長（CCO）以具體法規痛點關鍵字（如「創投」、「不動產抵押」、「洗錢」、「餘屋貸款」、「交易室門禁」、「審計委員會」）秒級檢索歷史具體缺失態樣與官方指引。

### 核心情境三：檢查局年度實地檢查量能與機構執行統計 (`f40_inspection_execution`)
- 統計 111~113 歷年檢查局針對受檢機構之檢查量能分佈。
- 區分檢查性質：
  1. `一般檢查`：針對金控 (6家)、本國銀行 (47家)、外國銀行分行 (13家)、證券商/投信 (26家)、壽險/產險等全面體檢。
  2. `專案檢查`：針對特定高風險業務（如不動產授信專案、防洗專案、資安專案）定點打擊。
  3. `受託檢查`：受託辦理農業金融機構及資訊共用中心（高達 115 家）之實地金融檢查，串接 `tw-agro-db`。

### 核心情境四：重大內控與法遵高頻缺失結構檢視表 (`v_f40_deficiency_category_summary`)
- 自動按受檢業別分組，聚合各項業務之缺失累計件數與佔比 (`category_pct`)。
- 精確量化金控集團內部管理 (18.18%)、子公司管理 (16.67%) 與公司治理 (16.67%) 之高頻破口，為政策監理提供量化雷達。

---

## 2. 核心資料庫模型與 DDL 規格 (`schema.sql`)

### 2.1 金融機構實地檢查重大缺失明細表 (`f40_exam_deficiencies`)
```sql
CREATE TABLE IF NOT EXISTS f40_exam_deficiencies (
    deficiency_uid TEXT PRIMARY KEY,      -- DEF_{sector}_{year}_{half}_{hash}
    target_sector TEXT NOT NULL,          -- 受檢業別: HOLDING(金控公司), FOREIGN_BANK(外銀在臺分行)
    eval_year TEXT NOT NULL,              -- 檢查年度 (ISO: YYYY)
    half_year TEXT NOT NULL,              -- 上半年 / 下半年 / 全年
    business_category TEXT NOT NULL,      -- 業務專案 (如 內部管理, 子公司管理, 公司治理, 風險管理, 授信業務, 防制洗錢)
    deficiency_pattern TEXT NOT NULL,     -- 缺失態樣 (核心違規摘要)
    deficiency_detail TEXT,               -- 缺失具體情節
    improvement_action TEXT,              -- 改善作法與遵循法令
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f40_sector ON f40_exam_deficiencies(target_sector);
CREATE INDEX IF NOT EXISTS idx_f40_year ON f40_exam_deficiencies(eval_year);
CREATE INDEX IF NOT EXISTS idx_f40_category ON f40_exam_deficiencies(business_category);
```

### 2.2 檢查局重大缺失全文檢索虛擬表 (`f40_deficiencies_fts`)
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS f40_deficiencies_fts USING fts5(
    deficiency_uid UNINDEXED,
    target_sector UNINDEXED,
    business_category,
    deficiency_pattern,
    deficiency_detail,
    improvement_action,
    tokenize='unicode61'
);
```

### 2.3 檢查局檢查性質與受檢機構年度執行統計表 (`f40_inspection_execution`)
```sql
CREATE TABLE IF NOT EXISTS f40_inspection_execution (
    stat_uid TEXT PRIMARY KEY,            -- EXEC_{year}_{exam_type}_{sector}
    eval_year TEXT NOT NULL,              -- 統計年度 (ISO: YYYY)
    exam_type TEXT NOT NULL,              -- 檢查性質 (一般檢查, 專案檢查, 受託檢查)
    target_sector TEXT NOT NULL,          -- 金融業別 (金控公司, 本國銀行, 外國銀行在臺分行, 產壽險, 農業金融機構)
    inspected_count INTEGER NOT NULL,     -- 受檢機構家數
    updated_at TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{"_v":"1.0.0"}'
);
CREATE INDEX IF NOT EXISTS idx_f40_exec_year ON f40_inspection_execution(eval_year);
```

### 2.4 業務專案高頻缺失分析檢視表 (`v_f40_deficiency_category_summary`)
```sql
CREATE VIEW IF NOT EXISTS v_f40_deficiency_category_summary AS
SELECT 
    target_sector,
    business_category,
    COUNT(*) AS deficiency_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM f40_exam_deficiencies d2 WHERE d2.target_sector = d1.target_sector), 2) AS category_pct
FROM f40_exam_deficiencies d1
GROUP BY target_sector, business_category
ORDER BY target_sector, deficiency_count DESC;
```

---

## 3. Python 核心 API 介面規格 (`commands_f40.py`)

1. `search_exam_deficiencies(db_path, keyword, target_sector=None, limit=10)`:
   - 優先調用 `f40_deficiencies_fts` MATCH 查詢；無結果時平滑 fallback 至 LIKE 模糊比對。
2. `query_deficiency_categories(db_path, target_sector=None)`:
   - 查詢業務專案缺失排行榜，回傳 `deficiency_count` 與 `category_pct`。
3. `query_inspection_executions(db_path, eval_year=None, limit=15)`:
   - 查詢實地檢查執行家數排行與檢查性質分佈。
