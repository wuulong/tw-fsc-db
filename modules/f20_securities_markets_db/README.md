# 📈 F20: 證券期貨與公開市場模組 (f20_securities_markets_db)

本子模組為 `tw-fsc-db` (金融監督管理委員會開放資料智庫) Pillar 2 核心聚合業務模組。

## 📁 職責與架構
* **責任範圍**：管理公開發行公司基準資料（ISIN）、每月營業收入彙總、上市持股逾 10% 大股東名單與市場動能分析。
* **資料表命名空間**：統一強制前綴 `f20_*`：
  - `f20_companies`：公開發行公司主表 (ISIN、產業、市場別、掛牌日)。
  - `f20_monthly_revenues`：每月營業收入與 YoY 年增率。
  - `f20_major_shareholders`：持股逾 10% 大股東申報名單。
* **自包含獨立性**：
  - `schema.sql`：專屬 DDL 與跨表/跨模組檢視表。
  - `etl.py`：自包含清洗入庫腳本，支援 `--db` 參數，引用 `a00_core` 工具庫。
  - `commands_f20.py`：提供營收成長股篩選與公司 Profile 查詢 API。
  - `tests/test_f20.py`：8 大測試案例之獨立臨時庫自動化測試。
