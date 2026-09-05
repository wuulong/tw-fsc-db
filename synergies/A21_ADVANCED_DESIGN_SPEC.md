# 🔬 A21 進階設計與跨部會多 DB 事前穿透規格書 (A21_ADVANCED_DESIGN_SPEC.md)

* **專案代號**：`GOV-A21`
* **受控版本**：`v1.1.0`
* **母專案對接**：`GOV-300` (tw-gov-db) ↔ `GOV-A21` (tw-fsc-db) ↔ `GOV-A19` (tw-agro-db)

---

## 1. 跨部會多 DB 事前融合分析模型 (Cross-Agency Analytics)

金管會智庫與外部部會建立了三大事前融合模型：
1. **`v_fsc_agro_green_credit_mesh` (FSC 金融 x AGRO 農糧綠色永續融資聯防)**：
   - 串接 `tw-agro-db` 之 `farmers_assoc_directory` (342 家農漁會信用部) 與 `tw-fsc-db` 之 `f10_bank_asset_quality` 及 `f10_corporate_loan_trends`。
   - 計算城鄉普惠金融涵蓋率與極端農害救助低利貸款動能。
2. **`v_fsc_moi_land_exposure_radar` (FSC 放款 x MOI 國土分區地籍曝險雷達)**：
   - 串接 `tw-moi-db` 地籍段號 (`cadastral_id`) 與 `tw-fsc-db` 之 `f10_land_collateral_loans`。
   - 監控商業銀行土地抵押貸款是否存在違法擴張至「特定農業區」或「地質敏感區」之情事。
3. **`v_fsc_vasp_aml_penetration` (FSC 虛擬資產 x MOJ/CIB 司法防詐穿透模型)**：
   - 串接 `f60_vasp_compliance_registry` 與 `f10_financial_institutions` (法幣代管信託銀行) 及 `f50_sanctions`。
   - 實現輸入任一虛擬通貨平台，瞬間穿透法幣託管隔離狀態與該代管銀行過去有無重大洗防缺失。

---

## 2. 演演算法與指標計算 (Algorithm Specifications)

1. **土地融資比率安全邊際算式**：
   $$LandLoanRatio = rac{	ext{土地擔保放款餘額}}{	ext{總放款餘額}} 	imes 100\%$$
   若比率大於全體市場第 75 百分位數，標註黃色關注燈號；若超過 40% 臨界值，標註紅色風控警訊。
2. **上市櫃本益比負值容錯演演算法**：
   若每股盈餘 $EPS \le 0$，動態轉譯為「虧損公司」指標，防止數學分母為零產生除法溢位。
3. **跨部會地址模糊正規化與 WGS84 空間碰撞演演算法**：
   調用 G300 `admin_codes` 與 `zipcode_registry`，將非標準中文地址轉換為標準 6 碼門牌區號與行政區碼。
