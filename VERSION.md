# 🏷️ tw-fsc-db (台灣金融監督管理開放資料智庫) 版本演進與開發歷程看板 (VERSION.md)

* **目前最新版本**：`v1.2.0`
* **發布日期**：2026-09-05
* **受控部會代號**：`GOV-A21` (金融監督管理委員會)
* **母專案基石**：`GOV-300` (`tw-gov-db`)
* **專書規範版本**：Book Governance Spec (BGS) `v2.0`
* **腳本治理規格**：CLI Governance Spec (CGS) `v2.1`
* **歸檔路徑**：[VERSION.md](VERSION.md)

---

## 📜 版本演進與 F-P-I-E-C 生命週期紀錄

### 🚀 `v1.2.0` (2026-09-05) - GOV-A21 ↔ GOV-300 跨部會通用基石對接整合對接與 100% 綠燈驗證大里程碑
* **生命週期狀態**：🟢 `COMPLETED` (跨部會對接驗證正式通過版)
* **技術專書版本 (Book Version)**：**`v1.2.0`**（依據 BGS v2.0 規格，全書對齊母大腦通用基石與對接合約）
* **相容性矩陣 (Cross-Project Compatibility Matrix)**：
  - **母基石專案**：`tw-gov-db (GOV-300)` **`v0.2.1`** 相容
  - **跨部會對接狀態**：🟢 **`Bootstrapped (已完成全路徑對接驗證)`**
  - **五大基石柱對齊**：OID `2.16.886.101.20003.20052`、板橋區 6 碼門牌 `650001`、8 碼統一編號法人柱、ISO-8601 時間柱
* **重點交付里程碑**：
  1. **跨部會 Synergy 協同合約與通用基石雙向串接連線 (4/4 綠燈 PASS)**：
     - 建立 `synergies/` 治理專區：`A21_SPECIFICATION.md`、`A21_ADVANCED_DESIGN_SPEC.md` 與 `GOV_A21_SYNERGY_SPEC.md` (軟連結 Symlink)。
     - **母大腦端實測通過 A21 提出的 4 大基石需求**：
       - `G300-REQ-FSC-01` (OID 權責歸併)：成功將處分書與名冊發布機關歸併至權威 OID (`2.16.886.101.20003.20052`)。
       - `G300-REQ-FSC-02` (6 碼門牌反查)：金管會總會所在地「新北市板橋區」精確命中門牌區號 **`650001`**（耗時 **0.986 ms**）。
       - `G300-REQ-FSC-03` (企業統編快取)：全台 2,590 家特許機構/上市櫃公司統編與 G300 `corporate_registry` 100% 對照寫入。
       - `G300-REQ-FSC-04` (跨部會 DB 直連)：母大腦 `DomainRegistryResolver` 直連 `db/fsc.db`，成功讀取 2,590 筆實體與 556 條集團拓樸。
  2. **母專案協同檔案對齊**：
     - 母專案 `tw-gov-db` 專書第 4 章正式收錄 `book/04_synergy_contracts/4.A21_spec_gov_a21_synergy.md`，並更新總目錄 `00_toc.md`。
     - 母子雙向 Prompt 契約就位：`PROMPT_TO_MASTER_G300.md` 與 `PROMPT_TO_SUBMODULE_A21.md`。
  3. **程式庫基石功能擴充**：
     - `src/a00_core/fsc_core.py` 新增 `query_g300_admin_code()` 直連 G300 universal_keys 反查 6 碼門牌。
     - `metadata.json` 與 `DATASETS.md` 正式註冊 G300 跨部會零重複基石清冊。

---

### 📘 `v1.1.0` (2026-09-05) - 開源技術專書完工大里程碑：全景圖鑑 (book/)、17 幅 Mermaid 架構圖與四大附錄
* **生命週期狀態**：🟢 `COMPLETED` (專書首發版)
* **重點變更**：
  - 完成開源技術專書 `book/`（第 0~6 章與 4 大附錄），並編譯產出 170KB 全書合訂本 `FULL_BOOK_TAIWAN_FSC_DB.md`。
  - 繪製全域拓樸 (Fig 2.1)、控制力圖 (Fig 2.2)、360° 流向圖 (Fig 2.3) 與 17 幅 Mermaid 圖表。
  - 完成第 3 章各子模組獨立篇章 (`03_00` 至 `03_60`) 與 Samples 微型真值樣本連結。
  - 完成第 4 章四大利害關係人實戰作戰劇本 (Playbook)。
  - 完成附錄 B 官方 25 個資料集 data.gov.tw 真實 Dataset ID 對照清單。

---

### 🏆 `v1.0.0` (2026-09-05) - 程式碼庫完整釋出版：六大業務模組落地、100% 綠燈單元測試網與開源 Submodule 納管
* **生命週期狀態**：🟢 `COMPLETED` (正式程式碼庫釋出版本)
* **重點變更**：
  - 整合 25 個官方資料集，入庫 18,624 筆真實地面資料，支援 FTS5 倒排檢索引擎。
  - 封裝 `fsc_cli.py` 統一命令列介面 (CGS v2.1)。
  - 單元測試網 `tests/test_fsc.py` 達成 100% 綠燈通過 (9/9 PASS)。
  - 實作智慧同步防護器 `sync_guard.py` 與 `sync_extension.py` 外接儲存管線。
  - 初始化獨立 Git 儲存庫並作為 Submodule 納入父專案。

---

### 🔨 `v0.8.0` (2026-09-05) - 系統工程 22 階段全涵蓋、智慧更新防護與外接磁碟管線
* **生命週期狀態**：🟢 `COMPLETED`

---

### 🧪 `v0.5.0` (2026-09-05) - 六大領域模組 DDL、ETL 與 FTS5 倒排檢索引擎實裝
* **生命週期狀態**：🟢 `COMPLETED`

---

### 🌱 `v0.1.0` (2026-09-05) - 專案初始化與三位一體規格先行 (Spec-First)
* **生命週期狀態**：🟢 `COMPLETED`
