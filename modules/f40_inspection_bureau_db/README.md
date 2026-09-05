# 📦 [模組代號] - [模組名稱]

本子模組為 `tw-fsc-db` (金融監督管理委員會開放資料智庫) 之標準垂直業務模組。

## 📁 檔案結構
* `schema.sql`: 模組專屬 DDL 與實體表結構定義。
* `etl.py`: 負責將開放資料 (CSV/JSON) 轉換正規化並灌入 SQLite。
* `metadata.json`: 模組中繼與資料源描述。
* `commands_[模組代號].py`: CLI 擴充指令。
