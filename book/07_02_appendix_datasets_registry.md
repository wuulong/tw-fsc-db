# 附錄 B：金管會 25 個官方資料集登記與下載清單 (data.gov.tw)

本附錄完整列出 `tw-fsc-db` 所整合收錄之全部 25 個官方開放資料來源。**資料集代號 100% 採用台灣政府資料開放平台 (data.gov.tw) 之真實原始 Dataset ID**（或官網動態公告之專案 Seed 標籤），絕不造假，方便各界直接於政府平台精確檢索、核對與下載原檔。

| 序號 | 政府開放資料集代號 (Dataset ID) | 官方資料集中文名稱 | 權責業務機關/局處 | 原始格式 | 映射本庫資料表 | 官方下載/來源連結 |
| :---: | :--- | :--- | :--- | :---: | :--- | :--- |
| **01** | `10689` | 金融控股公司設立情形表 | 金融監督管理委員會銀行局 | CSV | `f10_financial_holdings` | [下載/來源](https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking20.csv) |
| **02** | `10525` | 本國銀行逾放等財務資料 (Banking12) | 金融監督管理委員會銀行局 | CSV | `f10_bank_asset_quality` | [下載/來源](https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking12.csv) |
| **03** | `10552` | 以土地為擔保品之放款餘額資訊揭露 | 金融監督管理委員會銀行局 | CSV | `f10_land_financing_stats` | [下載/來源](https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking16.csv) |
| **04** | `11697` | 重要業務及財務資訊揭露-信用卡重要業務及財務資訊揭露 | 金融監督管理委員會銀行局 | CSV | `f10_credit_card_trends` | [下載/來源](https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking28.csv) |
| **05** | `13378` | 金融聯合徵信中心企業總貸款狀況統計趨勢資料(去識別化) | 金融監督管理委員會銀行局 | CSV | `f10_corporate_loans` | [下載/來源](https://www.jcic.org.tw/jcweb/en/services/inquiry/public/files/corporate_loan.CSV) |
| **06** | `28567` | 本國上市證券國際證券辨識號碼 (ISIN) | 金融監督管理委員會證券期貨局 | CSV | `f20_isin_companies` | [下載/來源](https://isin.twse.com.tw/isin/C_public.jsp?strMode=2) |
| **07** | `94026` | 公開發行公司每月營業收入彙總表 | 金融監督管理委員會證券期貨局 | CSV | `f20_monthly_revenues` | [下載/來源](https://mopsfin.twse.com.tw/opendata/t187ap05_P.csv) |
| **08** | `18422` | 上市公司持股逾10%大股東名單 | 金融監督管理委員會證券期貨局 | CSV | `f20_major_shareholders` | [下載/來源](https://mopsfin.twse.com.tw/opendata/t187ap02_L.csv) |
| **09** | `11373` | 上櫃股票個股本益比、殖利率、股價淨值比 | 金融監督管理委員會證券期貨局 | CSV | `f20_market_valuations` | [下載/來源](https://www.tpex.org.tw/web/stock/aftertrading/peratio_analysis/pera_result.php?l=zh-tw&o=csv) |
| **10** | `11359` | 期貨商交易量年報表 | 金融監督管理委員會證券期貨局 | CSV | `f20_futures_volumes` | [下載/來源](https://www.taifex.com.tw/cht/3/futDataDown) |
| **11** | `15326` | 會員名錄_壽險會員公司(保代同業公會) | 金融監督管理委員會保險局 | CSV | `f30_insurance_companies` | [下載/來源](https://www.ciaa.org.tw/EXPFILE.aspx?DATA=THAQTaH%2b1UsVu1u6Ao2TRw%3d%3d) |
| **12** | `7187` | 保險公司人力資源概況 | 金融監督管理委員會保險局 | JSON | `f30_insurance_hr` | [下載/來源](https://ins-info.ib.gov.tw/opendata/json-05020511.aspx) |
| **13** | `14504` | 人身保險申訴案件統計表 | 金融監督管理委員會保險局 | CSV | `f30_dispute_complaints_trends` | [下載/來源](https://openapi.tii.org.tw/TIIOPENDATA/API/CSV_EXPORT?TableID=I23) |
| **14** | `14505` | 特別補償基金統計表 | 金融監督管理委員會保險局 | CSV | `f30_special_compensation_fund` | [下載/來源](https://openapi.tii.org.tw/TIIOPENDATA/API/CSV_EXPORT?TableID=I25) |
| **15** | `10414` | 內控聲明書-外國銀行在臺分行 | 金融監督管理委員會檢查局 | CSV | `f40_internal_control_foreign_bank` | [下載/來源](https://www.feb.gov.tw/uploaddowndoc?file=opendata/202411151724161.csv&filedisplay=%E5%85%A7%E6%8E%A7%E8%81%B2%E6%98%8E%E6%9B%B8-%E5%A4%96%E5%9C%8B%E9%8A%80%E8%A1%8C%E5%9C%A8%E8%87%BA%E5%88%86%E8%A1%8C.csv&flag=doc) |
| **16** | `10435` | 金融機構主要檢查缺失-金控公司 | 金融監督管理委員會檢查局 | CSV | `f40_exam_deficiencies_fhc` | [下載/來源](https://www.feb.gov.tw/uploaddowndoc?file=opendata/202101291752052.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%A9%9F%E6%A7%8B%E4%B8%BB%E8%A6%81%E6%AA%A2%E6%9F%A5%E7%BC%BA%E5%A4%B1-%E9%87%91%E8%9E%8D%E6%8E%A7%E8%82%A1%E5%85%AC%E5%8F%B8.csv&flag=doc) |
| **17** | `10437` | 金融機構主要檢查缺失-外國銀行在臺分行 | 金融監督管理委員會檢查局 | CSV | `f40_inspection_findings` | [下載/來源](https://www.feb.gov.tw/uploaddowndoc?file=opendata/202412201417450.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%A9%9F%E6%A7%8B%E4%B8%BB%E8%A6%81%E6%AA%A2%E6%9F%A5%E7%BC%BA%E5%A4%B1-%E5%A4%96%E5%9C%8B%E9%8A%80%E8%A1%8C%E5%9C%A8%E8%87%BA%E5%88%86%E8%A1%8C.csv&flag=doc) |
| **18** | `10444` | 金融檢查執行情形 | 金融監督管理委員會檢查局 | CSV | `f40_inspection_execution` | [下載/來源](https://www.feb.gov.tw/uploaddowndoc?file=opendata/202101291831320.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%AA%A2%E6%9F%A5%E5%9F%B7%E8%A1%8C%E6%83%85%E5%BD%A2.csv&flag=doc) |
| **19** | `10292` | 金管會重大裁罰案件 | 金融監督管理委員會 | XML | `f50_sanction_records` | [下載/來源](https://www.fsc.gov.tw/RSS/Messages?serno=201202290003&language=chinese) |
| **20** | `11897` | 金融消費評議中心申訴案件統計表 | 金融監督管理委員會 | CSV | `f50_ombudsman_cases` | [下載/來源](https://www.foi.org.tw/infoshare/opendata/foiopendata.aspx?filetype=111) |
| **21** | `11198` | 金管會打詐儀表板-違規投資廣告蒐報成果 | 金融監督管理委員會證券期貨局 | CSV | `f50_antifraud_dashboard` | [下載/來源](https://www.sfb.gov.tw/uploaddowndoc?file=opendata/202412161656230.csv&filedisplay=%E9%87%91%E7%AE%A1%E6%9C%83%E6%89%93%E8%A9%90%E5%84%80%E8%A1%A8%E6%9D%BF.csv&flag=doc) |
| **22** | `11721` | 信託業商業同業公會相關法規 | 金融監督管理委員會 | XML | `f50_regulations` | [下載/來源](https://www.trust.org.tw/rss/laws/get) |
| **23** | `SEED-FINTECH` | 金融科技創新實驗與監理沙盒核准名單 (Seed) | 金融監督管理委員會綜合規劃處 | JSON | `f60_fintech_sandbox_experiments` | [下載/來源](https://www.fsc.gov.tw/ch/home.jsp?id=561) |
| **24** | `SEED-VASP` | 洗錢防制法令遵循聲明之虛擬資產平台業者名冊 (Seed) | 金融監督管理委員會證券期貨局 | JSON | `f60_vasp_compliance_entities` | [下載/來源](https://www.sfb.gov.tw/ch/home.jsp?id=1054) |
| **25** | `16024` | 國家溫室氣體排放清冊報告(永續指標) | 環境部氣候變遷署 | CSV | `f60_ghg_emissions_timeseries` | [下載/來源](https://data.moenv.gov.tw/api/v2/ghg_p_02?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=ImportDate%20desc&format=CSV) |
