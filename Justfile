# Justfile for tw-fsc-db (金融監督管理委員會開放資料智庫)

PYTHON := "/Users/wuulong/opt/anaconda3/envs/m2504/bin/python"

# 1. 執行核心單元測試與母大腦連鎖驗證
# 1.1 執行 F00 通用庫與 Master Hub 獨立測試
test-f00:
	@echo "🧪 執行 F00 母模組獨立測試..."
	{{PYTHON}} modules/f00_master_hub/tests/test_f00.py

# 1.2 執行 F00 Master Hub 聚合全域倒排索引
build-f00:
	@echo "🌐 聚合全域倒排索引 (FTS5)..."
	{{PYTHON}} modules/f00_master_hub/etl.py

test:
	@echo "🧪 執行金管會核心與母大腦連鎖單元測試..."
	PYTHONPATH=src {{PYTHON}} tests/test_fsc_core.py


# 2.1 執行 F10 銀行與金控子模組獨立測試
test-f10:
	@echo "🧪 執行 F10 銀行子模組獨立測試..."
	{{PYTHON}} modules/f10_banking_credit_db/tests/test_f10.py

# 2.2 執行 F10 ETL 資料清洗入庫
etl-f10:
	@echo "📥 執行 F10 銀行與金控資料清洗入庫..."
	{{PYTHON}} modules/f10_banking_credit_db/etl.py


# 2.3 執行 F20 證券與公開市場子模組獨立測試 (8大測試案例)
test-f20:
	@echo "🧪 執行 F20 證券子模組獨立測試 (TCV-F20-001~008)..."
	{{PYTHON}} modules/f20_securities_markets_db/tests/test_f20.py

# 2.4 執行 F20 ETL 資料清洗入庫
etl-f20:
	@echo "📥 執行 F20 證券公發資料清洗入庫..."
	{{PYTHON}} modules/f20_securities_markets_db/etl.py

# 2.5 執行 F30 保險市場與精算子模組獨立測試
test-f30:
	@echo "🧪 執行 F30 保險子模組獨立測試..."
	{{PYTHON}} modules/f30_insurance_actuarial_db/tests/test_f30.py

# 2.6 執行 F30 ETL 資料清洗入庫
etl-f30:
	@echo "📥 執行 F30 保險市場資料清洗入庫..."
	{{PYTHON}} modules/f30_insurance_actuarial_db/etl.py

# 2.7 執行 F40 金融檢查重大缺失獨立測試
test-f40:
	@echo "🧪 執行 F40 金融檢查子模組獨立測試..."
	{{PYTHON}} modules/f40_inspection_bureau_db/tests/test_f40.py

# 2.8 執行 F40 ETL 資料清洗入庫
etl-f40:
	@echo "📥 執行 F40 金融檢查與缺失資料清洗入庫..."
	{{PYTHON}} modules/f40_inspection_bureau_db/etl.py

# 2.9 執行 F50 處分裁罰與評議爭議獨立測試
test-f50:
	@echo "🧪 執行 F50 處分裁罰子模組獨立測試..."
	{{PYTHON}} modules/f50_sanctions_legal_db/tests/test_f50.py

# 2.10 執行 F50 ETL 資料清洗入庫
etl-f50:
	@echo "📥 執行 F50 處分裁罰與評議爭議清洗入庫..."
	{{PYTHON}} modules/f50_sanctions_legal_db/etl.py

# 2.11 執行 F60 金融科技、VASP 與永續金融獨立測試
test-f60:
	@echo "🧪 執行 F60 金融科技與 VASP 子模組獨立測試..."
	{{PYTHON}} modules/f60_fintech_vasp_db/tests/test_f60.py

# 2.12 執行 F60 ETL 資料清洗入庫
etl-f60:
	@echo "📥 執行 F60 金融科技與永續資料清洗入庫..."
	{{PYTHON}} modules/f60_fintech_vasp_db/etl.py

# 2. 檢查 CLI 運作狀態
status:
	@echo "📊 檢查金管會 CLI 狀態..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py status

# 3. 開放資料全量同步與範例抽取
fsc-data-sync:
	@echo "🔄 執行開放資料同步與 20 筆樣本抽取..."
	{{PYTHON}} scripts/fsc_data_sync.py --sync-all

# 4. 週期性智慧檢查遠端更新 (ETag/SHA-256 智慧跳過，有變更才補充式更新)
fsc-data-check:
	@echo "🔍 週期性智慧檢查遠端更新 (Smart Sync)..."
	{{PYTHON}} scripts/fsc_data_sync.py --check-updates

# 5. 檢查開放資料與樣本狀態
fsc-data-status:
	@echo "📊 檢查開放資料原始檔與樣本狀態..."
	{{PYTHON}} scripts/fsc_data_sync.py --status


# 5. 台灣語境淨化
sanitize:
	@echo "🧹 執行台灣語境用語淨化..."
	{{PYTHON}} ../../../scripts/utils/sanitize_locale_terms.py --path . --fix


# 6. 調閱 360 度跨模組全景實體檔案
fsc-profile query:
	@echo "🏛️ 調閱 360 度全景實體檔案: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py profile {{query}}

# 7. 銀行模組多維業務查詢
fsc-bank-land limit="5":
	@echo "🏞️ 查詢金融機構土地擔保放款排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py bank land -n {{limit}}

fsc-bank-cards limit="5":
	@echo "💳 查詢信用卡業務與簽帳消費力排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py bank cards -n {{limit}}

fsc-bank-corp limit="6":
	@echo "🏭 查詢全台企業總貸款月度趨勢 (近 {{limit}} 個月)..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py bank corporate -n {{limit}}

fsc-bank-radar limit="5":
	@echo "🛡️ 查詢商業銀行信用風險監理綜合雷達 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py bank radar -n {{limit}}

# 8. 證券期貨模組估值與期貨查詢
fsc-comp-val limit="5":
	@echo "💎 查詢股票市場估值與高殖利率排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py company valuation -n {{limit}}

fsc-comp-fut limit="5":
	@echo "📊 查詢期交所主力期貨合約交易排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py company futures -n {{limit}}

# 9. 保險市場精算與基金查詢
fsc-ins-list limit="10":
	@echo "🛡️ 查詢保險機構與精算配置排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py insurer list -n {{limit}}

fsc-ins-comp limit="5":
	@echo "⚖️ 查詢保險申訴爭議趨勢 (近 {{limit}} 年)..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py insurer complaints -n {{limit}}

fsc-ins-fund limit="5":
	@echo "🚗 查詢特別補償基金運作 (近 {{limit}} 年)..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py insurer fund -n {{limit}}

# 10. 集團股權與控制力網絡查詢
fsc-rel query:
	@echo "🕸️ 查詢金融集團控制鏈與大股東拓樸: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py relations {{query}}

# 11. 金融檢查重大缺失與執行統計查詢
fsc-exam-search query limit="5":
	@echo "🔍 FTS5 全文檢索金融檢查重大缺失: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py exam search {{query}} -n {{limit}}

fsc-exam-cats sector="HOLDING":
	@echo "📊 查詢重大缺失業務項目分佈統計 ({{sector}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py exam categories --sector {{sector}}

fsc-exam-exec limit="5":
	@echo "🏛️ 查詢檢查局年度實地檢查家數統計 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py exam execution -n {{limit}}
# 12. 處分裁罰與評議爭議查詢
fsc-sanc-search query limit="5":
	@echo "⚖️ FTS5 全文檢索重大裁罰處分書: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py sanction search {{query}} -n {{limit}}

fsc-sanc-top limit="5":
	@echo "🏆 查詢受裁罰機構累計罰鍰與案件排行 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py sanction top -n {{limit}}

fsc-sanc-cases limit="5":
	@echo "📢 查詢金融消費評議爭議申訴統計 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py sanction cases -n {{limit}}

fsc-sanc-esc query:
	@echo "🔍 重大缺失 ➔ 監理裁罰升級演進追蹤: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py sanction escalation {{query}}

# 13. 金融科技、VASP 與 ESG 永續查詢
fsc-fintech-vasp limit="5":
	@echo "🪙 查詢虛擬資產平台 (VASP) 洗防名冊 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py fintech vasp -n {{limit}}

fsc-fintech-sandbox limit="5":
	@echo "🔬 查詢金融科技監理沙盒創新實驗 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py fintech sandbox -n {{limit}}

fsc-fintech-esg limit="5":
	@echo "🌱 查詢國家溫室氣體排放時序 (Top {{limit}})..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py fintech esg -n {{limit}}

fsc-fintech-pen query:
	@echo "🔍 沙盒創新案 ➔ 合作特許銀行體質穿透: {{query}}..."
	PYTHONPATH=src {{PYTHON}} src/cli/fsc_cli.py fintech penetrate {{query}}
