# 🚀 fsc 金融監督管理委員會 開放資料圖鑑與智庫專案 (`tw-fsc-db`)

* **行政院部會權威程式碼 (Domain Code)**：`GOV-A21`
* **官方主管機關 OID**：`2.16.886.101.20003.20022`
* **三位一體典範**：`book/` (開源技術專書) + `db/` (SQLite 業務庫) + `src/` (Python/Typer CLI) + `sys_eng/` (系統工程)

---

## 🏛️ 1. 本專案核心架構與 `tw-gov-db` (GOV-300) 母大腦連鎖

本專案係遵循 **`[SPC-011]` 方案 A 權威命名規範** 建立之獨立部會專案。

### 🌐 零重複、100% 引用母大腦通用 Library (Zero Duplication Rule)
本專案**嚴禁重複複製**全台灣 368 鄉鎮區碼、122 條水系程式碼或 8 碼統一編號。所有五大基石的驗證與全島通配檢索，一律透過 `DomainRegistryResolver` 動態調用 `tw-gov-db` 通用程式庫與 `universal_keys.sqlite`。

```python
from a00_core.fsc_core import get_mother_gov_resolver

resolver = get_mother_gov_resolver()
# 連線至 GOV-300 母專案 universal_keys.sqlite 查詢
conn = resolver.get_domain_core_db_connection("GOV-300", "universal_keys")
```

---

## 📁 2. 目錄結構

```text
.
├── Justfile                          # CGS v2.1 & Just 自動化控制檔
├── metadata.json                     # 本專案權威 OID 與基石對齊聲明
├── README.md                         # 專案說明書
├── db/                               # SQLite 業務資料庫與 DDL
│   ├── schema.sql                    # 業務表 Schema (含五大基石外鍵)
│   └── fsc.meta.json                 # 資料庫詮釋資料
├── modules/                          # 業務子模組庫 (銀行、證券、保險、檢查)
│   └── template_blueprint/           # 子模組藍圖範本
├── book/                             # 開源技術專書目錄
├── src/                              # 核心模組與 Typer CLI
│   ├── a00_core/                     # 核心 API 與適配器 (fsc_core.py)
│   └── cli/                          # fsc_cli.py 命令行工具
└── tests/                            # 預設綠燈單元測試
```

---

## 🗄️ 3. 資料庫配置與外部儲存路徑解析 (Database Configuration)

本專案之二進位 SQLite 資料庫 (`fsc.db`) 遵循開源釋出治理規範，**不 Commit 進入 Git 儲存庫**。
CLI 與各子模組會依照以下 **四階優先順序 (Priority Chain)** 自動偵測並掛載資料庫：

1. **第一優先：CLI `--db` 顯式參數**
   ```bash
   python src/cli/fsc_cli.py status --db /path/to/fsc.db
   ```
2. **第二優先：環境變數 `FSC_DB_PATH`**
   ```bash
   export FSC_DB_PATH="/Volumes/D2024/data/fsc-db-in/tw-fsc-db/db/fsc.db"
   python src/cli/fsc_cli.py status
   ```
3. **第三優先：外接擴充儲存裝置預設路徑 (Auto-detection)**
   * 系統會自動探測外接儲存路徑：`/Volumes/D2024/data/fsc-db-in/tw-fsc-db/db/fsc.db`，若磁碟已掛載且檔案存在則優先直連。
4. **第四優先：本地開發路徑 (Local Fallback)**
   * 本地儲存庫內路徑：`db/fsc.db`。

在執行 `python src/cli/fsc_cli.py status` 時，看板首行將明確印出當前生效之資料庫實體路徑與來源說明。
