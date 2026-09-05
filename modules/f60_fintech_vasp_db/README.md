# 🌐 F60: 金融科技、虛擬資產平台 (VASP) 與永續金融智庫 (f60_fintech_vasp_db)

本模組為金融監督管理委員會 (`GOV-A21`) 轄下第六大特許與新興業務核心智庫。專注於：
1. **虛擬通貨平台 (VASP) 洗錢防制法令遵循業者名冊**（8碼統編強制繫結、法幣代管信託銀行穿透）。
2. **金融科技創新實驗監理沙盒專案庫**（好好投資、阿爾發投顧等創新成果與特許銀行合作對位）。
3. **國家溫室氣體排放清冊報告**（1990~2024 年 35 筆全時序真實毛排碳、碳匯吸收與淨排碳指標）。

## 快速指令
* 執行獨立單元測試：`just test-f60`
* 執行全量 ETL 匯入：`just etl-f60`
* 查詢 VASP 名冊：`./pa fsc fintech vasp`
* 查詢監理沙盒案：`./pa fsc fintech sandbox`
* 查詢 ESG 碳排時序：`./pa fsc fintech esg`
* 跨模組沙盒穿透：`./pa fsc fintech penetrate <case_no/applicant>`
