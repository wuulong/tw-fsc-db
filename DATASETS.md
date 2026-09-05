# 🏛️ 金融監督管理委員會 (tw-fsc-db / GOV-A21) 開放資料集盤點手冊 (DATASETS.md)

本檔案盤點 `tw-fsc-db` 專案涵蓋之 25 個核心開放資料集，已依循 **「6 大粗粒度業務聚合架構」** 歸併至對應之領域模組。所有資料集均已抽取前 20 筆真實地面資料 (Ground Truth) 保存於 `data/samples/`。

---

## 📁 模組資料集歸併對照表

### 🏦 `F10: f10_banking_credit_db` (銀行與信用金融模組)
* **金控設立及子公司名冊**：`data/samples/f10_fhc_setup_sample.csv` (CSV, 3.6KB)
* **本國銀行營運品質 (Banking12)**：`data/samples/f10_banking12_sample.csv` (CSV, 1.5KB)
* **以土地為擔保品之放款餘額資訊揭露**：`data/samples/f10_land_loan_sample.csv` (CSV, 798B)
* **信用卡重要業務及財務資訊揭露**：`data/samples/f10_credit_card_sample.csv` (CSV, 2.4KB)
* **聯徵中心企業總貸款狀況統計趨勢**：`data/samples/f10_corporate_loan_sample.csv` (CSV, 857B)

### 📈 `F20: f20_securities_markets_db` (證券期貨與公開市場模組)
* **本國上市證券國際證券辨識號碼 (ISIN)**：`data/samples/f20_isin_companies_sample.csv` (HTML Table, 8.3MB)
* **公開發行公司每月營業收入彙總表**：`data/samples/f20_monthly_revenue_sample.csv` (CSV, 2.9KB)
* **上市公司持股逾 10% 大股東名單**：`data/samples/f20_major_shareholders_sample.csv` (CSV, 1.0KB)
* **上櫃股票個股本益比、殖利率、股價淨值比**：`data/samples/f20_market_valuation_sample.csv` (CSV, 1.2KB)
* **期貨商交易量年報表**：`data/samples/f20_futures_volume_sample.csv` (CSV, 770B)

### 🛡️ `F30: f30_insurance_supervision_db` (保險監理與風險保障模組)
* **壽險會員公司名錄**：`data/samples/f30_life_insurance_members_sample.csv` (CSV, 41B)
* **保險公司人力資源概況**：`data/samples/f30_insurance_hr_sample.json` (CSV, 4.1KB)
* **人身保險申訴案件統計表**：`data/samples/f30_insurance_complaints_sample.csv` (CSV, 1.7KB)
* **特別補償基金統計表**：`data/samples/f30_special_compensation_fund_sample.csv` (CSV, 770B)

### 🔍 `F40: f40_financial_inspection_db` (金融檢查與內控治理模組)
* **內控聲明書 (外國銀行在臺分行)**：`data/samples/f40_internal_control_foreign_bank_sample.csv` (CSV, 927B)
* **金融機構主要檢查缺失 (金控公司)**：`data/samples/f40_exam_deficiencies_fhc_sample.csv` (CSV, 12.6KB)
* **金融機構主要檢查缺失 (外國銀行在臺分行)**：`data/samples/f40_inspection_priorities_sample.csv` (CSV, 14.8KB)
* **金融檢查執行情形**：`data/samples/f40_inspection_execution_sample.csv` (CSV, 857B)

### ⚖️ `F50: f50_sanctions_consumer_db` (裁罰、消保與防詐模組)
* **金管會重大裁罰案件 RSS**：`data/samples/f50_sanctions_rss_sample.xml` (RSS XML, 47.8KB)
* **金融消費評議中心申訴案件統計表**：`data/samples/f50_ombudsman_cases_sample.csv` (CSV, 1.4KB)
* **金管會打詐儀表板-違規投資廣告蒐報成果**：`data/samples/f50_antifraud_dashboard_sample.csv` (CSV, 589B)
* **信託業商業同業公會相關法規**：`data/samples/f50_regulations_sample.xml` (CSV, 6.9KB)

### 🌐 `F60: f60_fintech_esg_db` (金融科技、VASP與永續金融模組)
* **金融科技創新實驗與監理沙盒核准名單 (Seed)**：`data/samples/f60_fintech_sandbox_sample.json` (JSON, 554B)
* **洗錢防制法令遵循聲明之虛擬資產平台業者名冊 (Seed)**：`data/samples/f60_vasp_compliance_sample.json` (JSON, 1.1KB)
* **國家溫室氣體排放清冊報告 (永續指標)**：`data/samples/f60_greenhouse_gas_sample.csv` (CSV, 2.0KB)
