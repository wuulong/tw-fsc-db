# 🚀 任務指示：GOV-300 (tw-gov-db) ↔ GOV-A21 (tw-fsc-db) 跨部會對接母大腦端實作與驗證

你現在是 **`GOV-300` (`tw-gov-db` 全政府母大腦基石庫)** 的 Agentic AI 開發專家。

子專案 **`GOV-A21` (金管會 `tw-fsc-db`)** 已經完成程式碼庫 (v1.0.0) 與開源技術專書 (v1.1.0)，並將權威對接規格 (Synergy Spec) 歸位至 `GOV_A21_SYNERGY_SPEC.md`。請依據契約規範，完成母大腦端的對接能力驗證！

---

## 📍 權威對接規格參照 (Synergy Spec Reference)
請使用 `view_file` 讀取對接合約：
📄 `book/04_synergy_contracts/4.A21_spec_gov_a21_synergy.md`
重點查看 **第 2.2 節 (金管會專案對母專案 GOV-300 提出之基石需求規格)**。

---

## 🎯 你的 3 大執行任務：

### 1. 驗證與確保母大腦 4 大基石介面 (G300 Implementation Verification)
請確認 `GOV-300` 的 `src/core/` 已具備並暴露以下對接能力：
- **`G300-REQ-FSC-01` (OID 歸併)**：`BaseDomainAdapter.align_publisher_oid()` 支援帶入「金融監督管理委員會」或「銀行局」，回傳對應 OID `2.16.886.101.20003.20052.*`。
- **`G300-REQ-FSC-02` (門牌反查)**：`universal_keys.sqlite` 暴露 `admin_codes` 表，帶入「新北市板橋區」回傳 6 碼門牌區號 `650001`。
- **`G300-REQ-FSC-03` (企業統編快取)**：`corporate_registry` 支援統編反查與快取穿透。
- **`G300-REQ-FSC-04` (跨部會調度)**：`DomainRegistryResolver` 支援 `get_domain_core_db_connection("GOV-A21", "fsc.db")` 直連。

### 2. 執行母大腦端對接整合測試
請在專案中執行對接測試：
`python3 synergies/test_gov_a21_synergy.py`
確保 4 階測試 100% 綠燈通過！
