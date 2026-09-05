# 附錄 C：fsc_cli.py 命令列工具參數與指令速查手冊

`fsc_cli.py` 是本專案的核心統一命令列入口。支援標準 STDOUT/STDERR 管線分離、JSON 結構化輸出 (`-j`) 與安靜模式 (`-q`)。

---

## C.1 通用全域選項 (Global Flags)
```bash
python fsc_cli.py [MODULE] [COMMAND] [ARGS...] [OPTIONS]
```
- `-j`, `--json`：以純 JSON 格式輸出至標準輸出 (STDOUT)，便於 jq 或管線下游腳本解析。
- `-q`, `--quiet`：安靜模式，關閉所有載入中旋轉動畫、彩色邊框與提示資訊。
- `-l <N>`, `--limit <N>`：限制查詢結果回傳筆數 (預設依指令為 10~25 筆)。
- `-v`, `--version`：印出目前 CLI 工具規格版本 (CGS v2.1)。

---

## C.2 完整子指令清單速查表

| 指令群 | 子指令名稱 | 常用參數範例 | 說明 |
| :--- | :--- | :--- | :--- |
| **基礎維護** | `version` | `fsc version` | 輸出 CGS 規格版本與底層資料庫路徑 |
| | `stats` | `fsc stats` | 輸出全庫 6 大模組資料表與筆數態勢總覽 |
| **F00 母實體** | `entity` | `fsc entity 16834044` | 依統編或機構名稱查詢集團版圖與子公司 |
| | `search` | `fsc search "國泰"` | 模糊檢索全台 2,609 家金融特許機構 |
| **F10 銀行** | `bank list` | `fsc bank list -l 20` | 列出全台本國銀行程式碼與總行名冊 |
| | `bank credit-card`| `fsc bank credit-card -l 5` | 檢索最新全台信用卡簽帳金額與活卡率消長 |
| | `bank mortgage` | `fsc bank mortgage` | 計算並列出全市場土地擔保融資比率水位 |
| **F20 證券** | `company list` | `fsc company list -l 10` | 查詢上市櫃公開發行公司名冊 |
| | `company valuation`| `fsc company valuation` | 查詢市場本益比、殖利率與 P/B 評價 |
| | `company shareholders`| `fsc company shareholders` | 檢索大股東持股集中度與股權控制力 |
| **F30 保險** | `insurer list` | `fsc insurer list` | 產壽險機構清單與精算/核保專業人力分佈 |
| | `insurer complaints`| `fsc insurer complaints` | 查詢 25 年跨期申訴爭議比率歷史走勢 |
| | `insurer fund` | `fsc insurer fund` | 查詢汽車交通事故特別補償基金資料 |
| **F40 金檢** | `exam search` | `fsc exam search "內控"` | 透過 FTS5 全文檢索 100 筆重大金檢缺失態樣 |
| | `exam categories` | `fsc exam categories` | 列出金檢高頻缺失態樣排行統計 |
| | `exam execution` | `fsc exam execution` | 歷年金檢受檢頻次與局處排查統計 |
| **F50 處分** | `sanctions search`| `fsc sanctions search "洗錢"` | 檢索 499 筆處分裁罰案由、法規依據與金額 |
| | `sanctions stats` | `fsc sanctions stats` | 歷年各主管局處裁罰件數與罰鍰金額高峰 |
| | `ombudsman stats` | `fsc ombudsman stats` | 金融消費評議中心受理案量與和解率分析 |
| **F60 科技** | `fintech vasp` | `fsc fintech vasp` | 調閱 26 家完成洗防遵循聲明之 VASP 名冊 |
| | `fintech sandbox` | `fsc fintech sandbox` | 追蹤金管會創新實驗監理沙盒案現況 |
| | `fintech esg` | `fsc fintech esg` | 查詢 35 年國家溫室氣體時序排放資料 |
| | `fintech penetrate`| `fsc fintech penetrate 1`| 穿透指定沙盒專案與合作銀行之代管關係 |
| | `fintech aml-check`| `fsc fintech aml-check "幣託"`| 虛擬資產業者與代管銀行之洗防聯防排查 |
