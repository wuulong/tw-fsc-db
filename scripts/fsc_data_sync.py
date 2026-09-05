#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: fsc_data_sync.py
title: 金管會 (tw-fsc-db / GOV-A21) 開放資料同步、範例抽取與結構檢測工具 (CGS v2.1)
description: 自動化下載六大業務模組之開放資料與種子快照，抽取前 20 筆 Samples 微型範例，檢驗欄位結構並產出 DATASETS.md 盤點清單。
category: maintenance
manual: scripts/manuals/fsc_data_sync.md
dependencies: urllib, json, csv, os, sys, argparse, sqlite3
cgs_version: 2.1
"""

import os
import sys
import json
import csv
import io
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

__cli_spec_version__ = "2.1"

# 基準目錄定位
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLES_DIR = DATA_DIR / "samples"
# 引用 a00_core 工具與智慧同步防護器
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from a00_core.utils.sync_guard import compute_file_sha256, check_remote_header_modified, should_skip_update_by_hash
from a00_core.fsc_core import get_fsc_db_path

SYNC_META_PATH = DATA_DIR / ".sync_manifest.json"

# 定義六大業務模組之核心資料來源矩陣 (對齊 6 大粗粒度業務聚合模組)
DATASET_REGISTRY = [
    # --- Pillar 1: 銀行與信用金融 (F10) ---
    {
        "pillar": "Pillar 1: 銀行與信用金融",
        "module_id": "f10_banking_credit_db",
        "dataset_id": "10689",
        "name": "金融控股公司設立情形表",
        "agency": "金融監督管理委員會銀行局",
        "format": "CSV",
        "url": "https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking20.csv",
        "local_raw_name": "f10_fhc_setup.csv",
        "local_sample_name": "f10_fhc_setup_sample.csv"
    },
    {
        "pillar": "Pillar 1: 銀行與信用金融",
        "module_id": "f10_banking_credit_db",
        "dataset_id": "10525",
        "name": "本國銀行逾放等財務資料 (Banking12)",
        "agency": "金融監督管理委員會銀行局",
        "format": "CSV",
        "url": "https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking12.csv",
        "local_raw_name": "f10_banking12.csv",
        "local_sample_name": "f10_banking12_sample.csv"
    },
    {
        "pillar": "Pillar 1: 銀行與信用金融",
        "module_id": "f10_banking_credit_db",
        "dataset_id": "10552",
        "name": "以土地為擔保品之放款餘額資訊揭露",
        "agency": "金融監督管理委員會銀行局",
        "format": "CSV",
        "url": "https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking16.csv",
        "local_raw_name": "f10_land_loan.csv",
        "local_sample_name": "f10_land_loan_sample.csv"
    },
    {
        "pillar": "Pillar 1: 銀行與信用金融",
        "module_id": "f10_banking_credit_db",
        "dataset_id": "11697",
        "name": "重要業務及財務資訊揭露-信用卡重要業務及財務資訊揭露",
        "agency": "金融監督管理委員會銀行局",
        "format": "CSV",
        "url": "https://www.banking.gov.tw/webdowndoc?file=/stat/itopendata/banking28.csv",
        "local_raw_name": "f10_credit_card.csv",
        "local_sample_name": "f10_credit_card_sample.csv"
    },
    {
        "pillar": "Pillar 1: 銀行與信用金融",
        "module_id": "f10_banking_credit_db",
        "dataset_id": "13378",
        "name": "金融聯合徵信中心企業總貸款狀況統計趨勢資料(去識別化)",
        "agency": "金融監督管理委員會銀行局",
        "format": "CSV",
        "url": "https://www.jcic.org.tw/jcweb/en/services/inquiry/public/files/corporate_loan.CSV",
        "local_raw_name": "f10_corporate_loan.csv",
        "local_sample_name": "f10_corporate_loan_sample.csv"
    },

    # --- Pillar 2: 證券期貨與公開市場 (F20) ---
    {
        "pillar": "Pillar 2: 證券期貨與公開市場",
        "module_id": "f20_securities_markets_db",
        "dataset_id": "28567",
        "name": "本國上市證券國際證券辨識號碼 (ISIN)",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
        "local_raw_name": "f20_isin_companies.csv",
        "local_sample_name": "f20_isin_companies_sample.csv"
    },
    {
        "pillar": "Pillar 2: 證券期貨與公開市場",
        "module_id": "f20_securities_markets_db",
        "dataset_id": "94026",
        "name": "公開發行公司每月營業收入彙總表",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://mopsfin.twse.com.tw/opendata/t187ap05_P.csv",
        "local_raw_name": "f20_monthly_revenue.csv",
        "local_sample_name": "f20_monthly_revenue_sample.csv"
    },
    {
        "pillar": "Pillar 2: 證券期貨與公開市場",
        "module_id": "f20_securities_markets_db",
        "dataset_id": "18422",
        "name": "上市公司持股逾10%大股東名單",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://mopsfin.twse.com.tw/opendata/t187ap02_L.csv",
        "local_raw_name": "f20_major_shareholders.csv",
        "local_sample_name": "f20_major_shareholders_sample.csv"
    },
    {
        "pillar": "Pillar 2: 證券期貨與公開市場",
        "module_id": "f20_securities_markets_db",
        "dataset_id": "11373",
        "name": "上櫃股票個股本益比、殖利率、股價淨值比",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://www.tpex.org.tw/web/stock/aftertrading/peratio_analysis/pera_result.php?l=zh-tw&o=csv",
        "local_raw_name": "f20_market_valuation.csv",
        "local_sample_name": "f20_market_valuation_sample.csv"
    },
    {
        "pillar": "Pillar 2: 證券期貨與公開市場",
        "module_id": "f20_securities_markets_db",
        "dataset_id": "11359",
        "name": "期貨商交易量年報表",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://www.taifex.com.tw/cht/3/futDataDown",
        "local_raw_name": "f20_futures_volume.csv",
        "local_sample_name": "f20_futures_volume_sample.csv"
    },

    # --- Pillar 3: 保險監理與風險保障 (F30) ---
    {
        "pillar": "Pillar 3: 保險監理與風險保障",
        "module_id": "f30_insurance_supervision_db",
        "dataset_id": "15326",
        "name": "會員名錄_壽險會員公司(保代同業公會)",
        "agency": "金融監督管理委員會保險局",
        "format": "CSV",
        "url": "https://www.ciaa.org.tw/EXPFILE.aspx?DATA=THAQTaH%2b1UsVu1u6Ao2TRw%3d%3d",
        "local_raw_name": "f30_life_insurance_members.csv",
        "local_sample_name": "f30_life_insurance_members_sample.csv"
    },
    {
        "pillar": "Pillar 3: 保險監理與風險保障",
        "module_id": "f30_insurance_supervision_db",
        "dataset_id": "7187",
        "name": "保險公司人力資源概況",
        "agency": "金融監督管理委員會保險局",
        "format": "JSON",
        "url": "https://ins-info.ib.gov.tw/opendata/json-05020511.aspx",
        "local_raw_name": "f30_insurance_hr.json",
        "local_sample_name": "f30_insurance_hr_sample.json"
    },
    {
        "pillar": "Pillar 3: 保險監理與風險保障",
        "module_id": "f30_insurance_supervision_db",
        "dataset_id": "14504",
        "name": "人身保險申訴案件統計表",
        "agency": "金融監督管理委員會保險局",
        "format": "CSV",
        "url": "https://openapi.tii.org.tw/TIIOPENDATA/API/CSV_EXPORT?TableID=I23",
        "local_raw_name": "f30_insurance_complaints.csv",
        "local_sample_name": "f30_insurance_complaints_sample.csv"
    },
    {
        "pillar": "Pillar 3: 保險監理與風險保障",
        "module_id": "f30_insurance_supervision_db",
        "dataset_id": "14505",
        "name": "特別補償基金統計表",
        "agency": "金融監督管理委員會保險局",
        "format": "CSV",
        "url": "https://openapi.tii.org.tw/TIIOPENDATA/API/CSV_EXPORT?TableID=I25",
        "local_raw_name": "f30_special_compensation_fund.csv",
        "local_sample_name": "f30_special_compensation_fund_sample.csv"
    },

    # --- Pillar 4: 金融檢查與內控治理 (F40) ---
    {
        "pillar": "Pillar 4: 金融檢查與內控治理",
        "module_id": "f40_financial_inspection_db",
        "dataset_id": "10414",
        "name": "內控聲明書-外國銀行在臺分行",
        "agency": "金融監督管理委員會檢查局",
        "format": "CSV",
        "url": "https://www.feb.gov.tw/uploaddowndoc?file=opendata/202411151724161.csv&filedisplay=%E5%85%A7%E6%8E%A7%E8%81%B2%E6%98%8E%E6%9B%B8-%E5%A4%96%E5%9C%8B%E9%8A%80%E8%A1%8C%E5%9C%A8%E8%87%BA%E5%88%86%E8%A1%8C.csv&flag=doc",
        "local_raw_name": "f40_internal_control_foreign_bank.csv",
        "local_sample_name": "f40_internal_control_foreign_bank_sample.csv"
    },
    {
        "pillar": "Pillar 4: 金融檢查與內控治理",
        "module_id": "f40_financial_inspection_db",
        "dataset_id": "10435",
        "name": "金融機構主要檢查缺失-金控公司",
        "agency": "金融監督管理委員會檢查局",
        "format": "CSV",
        "url": "https://www.feb.gov.tw/uploaddowndoc?file=opendata/202101291752052.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%A9%9F%E6%A7%8B%E4%B8%BB%E8%A6%81%E6%AA%A2%E6%9F%A5%E7%BC%BA%E5%A4%B1-%E9%87%91%E8%9E%8D%E6%8E%A7%E8%82%A1%E5%85%AC%E5%8F%B8.csv&flag=doc",
        "local_raw_name": "f40_exam_deficiencies_fhc.csv",
        "local_sample_name": "f40_exam_deficiencies_fhc_sample.csv"
    },
    {
        "pillar": "Pillar 4: 金融檢查與內控治理",
        "module_id": "f40_financial_inspection_db",
        "dataset_id": "10437",
        "name": "金融機構主要檢查缺失-外國銀行在臺分行",
        "agency": "金融監督管理委員會檢查局",
        "format": "CSV",
        "url": "https://www.feb.gov.tw/uploaddowndoc?file=opendata/202412201417450.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%A9%9F%E6%A7%8B%E4%B8%BB%E8%A6%81%E6%AA%A2%E6%9F%A5%E7%BC%BA%E5%A4%B1-%E5%A4%96%E5%9C%8B%E9%8A%80%E8%A1%8C%E5%9C%A8%E8%87%BA%E5%88%86%E8%A1%8C.csv&flag=doc",
        "local_raw_name": "f40_inspection_priorities.csv",
        "local_sample_name": "f40_inspection_priorities_sample.csv"
    },
    {
        "pillar": "Pillar 4: 金融檢查與內控治理",
        "module_id": "f40_financial_inspection_db",
        "dataset_id": "10444",
        "name": "金融檢查執行情形",
        "agency": "金融監督管理委員會檢查局",
        "format": "CSV",
        "url": "https://www.feb.gov.tw/uploaddowndoc?file=opendata/202101291831320.csv&filedisplay=%E9%87%91%E8%9E%8D%E6%AA%A2%E6%9F%A5%E5%9F%B7%E8%A1%8C%E6%83%85%E5%BD%A2.csv&flag=doc",
        "local_raw_name": "f40_inspection_execution.csv",
        "local_sample_name": "f40_inspection_execution_sample.csv"
    },

    # --- Pillar 5: 裁罰、消保與防詐 (F50) ---
    {
        "pillar": "Pillar 5: 裁罰、消保與防詐",
        "module_id": "f50_sanctions_consumer_db",
        "dataset_id": "10292",
        "name": "金管會重大裁罰案件",
        "agency": "金融監督管理委員會",
        "format": "XML",
        "url": "https://www.fsc.gov.tw/RSS/Messages?serno=201202290003&language=chinese",
        "local_raw_name": "f50_sanctions_rss.xml",
        "local_sample_name": "f50_sanctions_rss_sample.xml"
    },
    {
        "pillar": "Pillar 5: 裁罰、消保與防詐",
        "module_id": "f50_sanctions_consumer_db",
        "dataset_id": "11897",
        "name": "金融消費評議中心申訴案件統計表",
        "agency": "金融監督管理委員會",
        "format": "CSV",
        "url": "https://www.foi.org.tw/infoshare/opendata/foiopendata.aspx?filetype=111",
        "local_raw_name": "f50_ombudsman_cases.csv",
        "local_sample_name": "f50_ombudsman_cases_sample.csv"
    },
    {
        "pillar": "Pillar 5: 裁罰、消保與防詐",
        "module_id": "f50_sanctions_consumer_db",
        "dataset_id": "11198",
        "name": "金管會打詐儀表板-違規投資廣告蒐報成果",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "CSV",
        "url": "https://www.sfb.gov.tw/uploaddowndoc?file=opendata/202412161656230.csv&filedisplay=%E9%87%91%E7%AE%A1%E6%9C%83%E6%89%93%E8%A9%90%E5%84%80%E8%A1%A8%E6%9D%BF.csv&flag=doc",
        "local_raw_name": "f50_antifraud_dashboard.csv",
        "local_sample_name": "f50_antifraud_dashboard_sample.csv"
    },
    {
        "pillar": "Pillar 5: 裁罰、消保與防詐",
        "module_id": "f50_sanctions_consumer_db",
        "dataset_id": "11721",
        "name": "信託業商業同業公會相關法規",
        "agency": "金融監督管理委員會",
        "format": "XML",
        "url": "https://www.trust.org.tw/rss/laws/get",
        "local_raw_name": "f50_regulations.xml",
        "local_sample_name": "f50_regulations_sample.xml"
    },

    # --- Pillar 6: 金融科技、VASP與永續金融 (F60) ---
    {
        "pillar": "Pillar 6: 金融科技、VASP與永續金融",
        "module_id": "f60_fintech_esg_db",
        "dataset_id": "SEED-FINTECH",
        "name": "金融科技創新實驗與監理沙盒核准名單 (Seed)",
        "agency": "金融監督管理委員會綜合規劃處",
        "format": "JSON",
        "url": "https://www.fsc.gov.tw/ch/home.jsp?id=561",
        "local_raw_name": "f60_fintech_sandbox.json",
        "local_sample_name": "f60_fintech_sandbox_sample.json"
    },
    {
        "pillar": "Pillar 6: 金融科技、VASP與永續金融",
        "module_id": "f60_fintech_esg_db",
        "dataset_id": "SEED-VASP",
        "name": "洗錢防制法令遵循聲明之虛擬資產平台業者名冊 (Seed)",
        "agency": "金融監督管理委員會證券期貨局",
        "format": "JSON",
        "url": "https://www.sfb.gov.tw/ch/home.jsp?id=1054",
        "local_raw_name": "f60_vasp_compliance.json",
        "local_sample_name": "f60_vasp_compliance_sample.json"
    },
    {
        "pillar": "Pillar 6: 金融科技、VASP與永續金融",
        "module_id": "f60_fintech_esg_db",
        "dataset_id": "16024",
        "name": "國家溫室氣體排放清冊報告(永續指標)",
        "agency": "環境部氣候變遷署",
        "format": "CSV",
        "url": "https://data.moenv.gov.tw/api/v2/ghg_p_02?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=ImportDate%20desc&format=CSV",
        "local_raw_name": "f60_greenhouse_gas.csv",
        "local_sample_name": "f60_greenhouse_gas_sample.csv"
    }
]

import ssl

# 提升 CSV 欄位限制防爆
csv.field_size_limit(sys.maxsize)

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url_content(url: str, timeout: int = 30) -> bytes:
    """透過 urllib 下載網址內容，帶標準 User-Agent"""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"}
    )
    with urllib.request.urlopen(req, context=get_ssl_context(), timeout=timeout) as response:
        return response.read()

def extract_samples(raw_path: Path, sample_path: Path, file_format: str, limit: int = 20) -> Dict[str, Any]:
    """從原始檔案中精確提取前 limit 筆為 Sample"""
    sample_path.parent.mkdir(parents=True, exist_ok=True)

    if file_format.upper() == "CSV":
        content = None
        for enc in ["utf-8-sig", "utf-8", "big5", "cp950"]:
            try:
                content = raw_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            content = raw_path.read_bytes().decode("utf-8", errors="ignore")

        if "<table" in content.lower():
            lines = content.splitlines()
            sample_lines = lines[:500]
            sample_path.write_text("\n".join(sample_lines), encoding="utf-8")
            return {"format": "HTML_TABLE", "sample_lines": len(sample_lines)}

        reader = csv.reader(io.StringIO(content))
        rows = []
        for i, row in enumerate(reader):
            if i > limit:
                break
            rows.append(row)

        with open(sample_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        return {"format": "CSV", "header_cols": len(rows[0]) if rows else 0, "sample_rows": len(rows) - 1}

    elif file_format.upper() == "JSON":
        try:
            data = json.loads(raw_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            data = json.loads(raw_path.read_text(encoding="big5"))

        if isinstance(data, list):
            sample_data = data[:limit]
        elif isinstance(data, dict):
            sample_data = {}
            for k, v in data.items():
                if isinstance(v, list):
                    sample_data[k] = v[:limit]
                else:
                    sample_data[k] = v
        else:
            sample_data = data

        sample_path.write_text(json.dumps(sample_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"format": "JSON", "sample_items": min(len(data) if isinstance(data, list) else 1, limit)}

    elif file_format.upper() == "XML":
        content = raw_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()[:100]
        sample_path.write_text("\n".join(lines), encoding="utf-8")
        return {"format": "XML", "sample_lines": len(lines)}

    return {"format": "UNKNOWN"}

def sync_datasets(download: bool = True, extract: bool = True) -> List[Dict[str, Any]]:
    """執行開放資料下載與範例抽取流水線"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for entry in DATASET_REGISTRY:
        item_res = {
            "module_id": entry["module_id"],
            "pillar": entry["pillar"],
            "name": entry["name"],
            "dataset_id": entry["dataset_id"],
            "agency": entry["agency"],
            "format": entry["format"],
            "local_raw_name": entry["local_raw_name"],
            "local_sample_name": entry["local_sample_name"],
            "url": entry["url"]
        }

        raw_p = RAW_DIR / entry["local_raw_name"]
        sample_p = SAMPLES_DIR / entry["local_sample_name"]

        # 1. 下載或注入種子
        if entry["dataset_id"] == "SEED-FINTECH":
            seed_data = [
                {
                    "case_no": "108001",
                    "applicant": "台北富邦商業銀行股份有限公司",
                    "experiment_name": "區塊鏈跨行轉帳試辦案",
                    "approval_date": "2019-04-30",
                    "status": "COMPLETED"
                },
                {
                    "case_no": "108002",
                    "applicant": "國泰世華商業銀行股份有限公司",
                    "experiment_name": "多元身分驗證金融創新服務",
                    "approval_date": "2019-11-15",
                    "status": "COMPLETED"
                },
                {
                    "case_no": "109001",
                    "applicant": "好好證券科技股份有限公司",
                    "experiment_name": "基金交換次級市場平臺",
                    "approval_date": "2020-05-12",
                    "status": "APPROVED_GRADUATED"
                },
                {
                    "case_no": "110001",
                    "applicant": "阿爾發證券投資顧問股份有限公司",
                    "experiment_name": "機器人理財顧問跨機構微型退休金投資方案",
                    "approval_date": "2021-08-20",
                    "status": "ACTIVE"
                }
            ]
            raw_p.write_text(json.dumps(seed_data, ensure_ascii=False, indent=2), encoding="utf-8")
            item_res["download_status"] = "LOCAL_SEED"
            item_res["raw_bytes"] = raw_p.stat().st_size
        elif entry["dataset_id"] == "SEED-VASP":
            seed_data = [
                {
                    "registration_no": "VASP-001",
                    "company_name": "現代財富科技有限公司",
                    "brand_name": "MaiCoin / MAX",
                    "tax_id": "54341909",
                    "compliance_date": "2021-10-01",
                    "business_type": "虛擬通貨買賣、交換、託管",
                    "status": "COMPLIANT"
                },
                {
                    "registration_no": "VASP-002",
                    "company_name": "幣託科技股份有限公司",
                    "brand_name": "BitoPro",
                    "tax_id": "54877708",
                    "compliance_date": "2021-10-15",
                    "business_type": "虛擬通貨買賣、交換、託管",
                    "status": "COMPLIANT"
                },
                {
                    "registration_no": "VASP-003",
                    "company_name": "王牌數位創新股份有限公司",
                    "brand_name": "ACE",
                    "tax_id": "56987114",
                    "compliance_date": "2021-11-01",
                    "business_type": "虛擬通貨買賣、交換",
                    "status": "COMPLIANT"
                },
                {
                    "registration_no": "VASP-004",
                    "company_name": "塞席爾商共識網股份有限公司台灣分公司",
                    "brand_name": "BitstreetX",
                    "tax_id": "83244837",
                    "compliance_date": "2022-01-10",
                    "business_type": "虛擬通貨交易平台",
                    "status": "COMPLIANT"
                }
            ]
            raw_p.write_text(json.dumps(seed_data, ensure_ascii=False, indent=2), encoding="utf-8")
            item_res["download_status"] = "LOCAL_SEED"
            item_res["raw_bytes"] = raw_p.stat().st_size

        elif download:
            if entry["url"].startswith("http"):
                try:
                    sys.stderr.write(f"📥 下載中: {entry['name']} ({entry['url']})\n")
                    content = fetch_url_content(entry["url"])
                    raw_p.write_bytes(content)
                    item_res["download_status"] = "OK"
                    item_res["raw_bytes"] = len(content)
                except Exception as e:
                    sys.stderr.write(f"⚠️ 下載失敗: {entry['name']} - {e}\n")
                    item_res["download_status"] = f"FAILED: {e}"
            else:
                item_res["download_status"] = "LOCAL_FILE"

        # 2. 抽取樣本
        if extract and raw_p.exists():
            try:
                sample_stats = extract_samples(raw_p, sample_p, entry["format"], limit=20)
                item_res["sample_status"] = "OK"
                item_res["sample_stats"] = sample_stats
            except Exception as e:
                item_res["sample_status"] = f"FAILED: {e}"
        else:
            item_res["sample_status"] = "RAW_NOT_FOUND"

        results.append(item_res)

    return results

def generate_datasets_md(results: List[Dict[str, Any]]) -> str:
    """生成正式 DATASETS.md 檔案內容"""
    lines = [
        "# 📚 金管會開放資料與種子資料集清單 (tw-fsc-db Datasets Manifest)",
        "",
        f"> **更新時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> **資料庫代號**：`tw-fsc-db` (`GOV-A21`)  ",
        "> **管理工具**：`scripts/fsc_data_sync.py`  ",
        "",
        "---",
        "",
        "## 1. 六大業務基石資料集盤點與下載矩陣",
        "",
        "| 業務基石 (Pillar) | 子模組 | 資料集名稱 | 提供機關 | 格式 | 樣本路徑 | 原始來源 URL |",
        "| :--- | :--- | :--- | :--- | :---: | :--- | :--- |"
    ]
    for r in results:
        sample_rel = f"`data/samples/{r['local_sample_name']}`"
        lines.append(
            f"| **{r['pillar']}** | `{r['module_id']}` | **{r['name']}** | {r['agency']} | {r['format']} | {sample_rel} | [{r['dataset_id']}]({r['url']}) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. 實體資料檔案結構與同步規範",
        "",
        "* **全量暫存區 (`data/raw/`)**：",
        "  - 存放自動同步下載之全量原始檔（CSV/XML/JSON）。",
        "  - 已加入 `data/.gitignore` 排除大檔，不污染 Git 倉庫。",
        "* **精簡樣本區 (`data/samples/`)**：",
        "  - 永久保留前 20 筆真實地面資料（Ground Truth Samples）。",
        "  - 納入版本控制並供開源釋出、離線單元測試與 CI 驗證。",
        "",
        "---",
        "",
        "## 3. 自動化同步與維護指令",
        "```bash",
        "# 1. 檢驗目前 samples 結構與狀態",
        "python scripts/fsc_data_sync.py --status",
        "",
        "# 2. 執行全量開放資料下載與範例抽取",
        "python scripts/fsc_data_sync.py --sync-all",
        "```",
        ""
    ])

    return "\n".join(lines)

def load_sync_manifest() -> Dict[str, Any]:
    """載入既有同步紀錄 (包含 etag, last_modified, sha256_hash, last_synced_at)"""
    if SYNC_META_PATH.exists():
        try:
            return json.loads(SYNC_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_sync_manifest(manifest: Dict[str, Any]):
    """儲存最新同步紀錄清單至 .sync_manifest.json"""
    SYNC_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYNC_META_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

def trigger_incremental_etl(module_id: str, custom_db: Optional[str] = None) -> Dict[str, Any]:
    """
    依模組代號動態呼叫對應模組之自包含 ETL 函式，進行補充式 (Upsert) 增量寫入
    """
    target_db, _ = get_fsc_db_path(custom_db)
    
    # 確保模組可在 sys.path 中被 import
    modules_dir = BASE_DIR / "modules"
    if str(modules_dir) not in sys.path:
        sys.path.insert(0, str(modules_dir))

    try:
        if module_id == "f10_banking_credit_db":
            from modules.f10_banking_credit_db.etl import run_f10_etl
            return run_f10_etl(target_db)
        elif module_id == "f20_securities_markets_db":
            from modules.f20_securities_markets_db.etl import run_f20_etl
            return run_f20_etl(target_db)
        elif module_id == "f30_insurance_supervision_db" or module_id == "f30_insurance_actuarial_db":
            from modules.f30_insurance_actuarial_db.etl import run_f30_etl
            return run_f30_etl(target_db)
        elif module_id == "f40_financial_inspection_db" or module_id == "f40_inspection_bureau_db":
            from modules.f40_inspection_bureau_db.etl import run_f40_etl
            return run_f40_etl(target_db)
        elif module_id == "f50_sanctions_consumer_db" or module_id == "f50_sanctions_legal_db":
            from modules.f50_sanctions_legal_db.etl import run_f50_etl
            return run_f50_etl(target_db)
        elif module_id == "f60_fintech_esg_db" or module_id == "f60_fintech_vasp_db":
            from modules.f60_fintech_vasp_db.etl import run_f60_etl
            return run_f60_etl(target_db)
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

    return {"status": "NO_ETL_DEFINED"}

def check_and_update_datasets(
    auto_etl: bool = True,
    custom_db: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    週期性智慧檢查更新流水線 (Smart Sync Pipeline):
    1. 對外部來源進行 HTTP HEAD / ETag 檢查，未修改則 0 流量跳過。
    2. 下載後進行檔案 SHA-256 內容雜湊比對，若內容完全相同則跳過重複入庫。
    3. 若真有新內容，抽取前 20 筆 Samples 並發動對應模組的補充式 ETL (INSERT OR REPLACE)。
    4. 最後若有任一模組更新，觸發 F00 母大腦重新聚合倒排索引 (FTS5)。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_sync_manifest()
    results = []
    modules_to_update = set()

    for entry in DATASET_REGISTRY:
        ds_id = entry["dataset_id"]
        local_raw = entry["local_raw_name"]
        raw_p = RAW_DIR / local_raw
        sample_p = SAMPLES_DIR / entry["local_sample_name"]
        
        item_res = {
            "module_id": entry["module_id"],
            "name": entry["name"],
            "dataset_id": ds_id,
            "url": entry["url"],
            "status": "UP_TO_DATE",
            "action": "SKIPPED"
        }

        # 處理本機種子檔案
        if ds_id.startswith("SEED-"):
            # 種子檔案比對本機 SHA-256
            if raw_p.exists():
                curr_hash = compute_file_sha256(raw_p)
                prev_record = manifest.get(ds_id, {})
                if prev_record.get("sha256_hash") == curr_hash:
                    item_res["action"] = "SKIPPED_SEED_UNCHANGED"
                else:
                    manifest[ds_id] = {
                        "sha256_hash": curr_hash,
                        "last_updated": datetime.now().isoformat()
                    }
                    modules_to_update.add(entry["module_id"])
                    item_res["action"] = "SEED_REGISTERED"
            results.append(item_res)
            continue

        prev_info = manifest.get(ds_id, {})
        prev_etag = prev_info.get("etag", "")
        prev_lm = prev_info.get("last_modified", "")
        prev_hash = prev_info.get("sha256_hash", "")

        # 步驟 1: HTTP HEAD 檢查 (若檔案已在本地且有標頭)
        if raw_p.exists() and (prev_etag or prev_lm):
            modified, new_headers = check_remote_header_modified(entry["url"], prev_etag, prev_lm)
            if not modified:
                item_res["action"] = "SKIPPED_HTTP_304"
                results.append(item_res)
                continue
        else:
            new_headers = {}

        # 步驟 2: 下載最新內容
        try:
            sys.stderr.write(f"📥 探測/下載: {entry['name']}...\n")
            content = fetch_url_content(entry["url"])
        except Exception as e:
            item_res["status"] = "ERROR"
            item_res["action"] = f"DOWNLOAD_FAILED: {e}"
            results.append(item_res)
            continue

        # 計算下載內容雜湊
        new_hash = hashlib.sha256(content).hexdigest()
        if raw_p.exists() and new_hash == prev_hash:
            item_res["action"] = "SKIPPED_HASH_MATCH"
            results.append(item_res)
            continue

        # 步驟 3: 寫入新 raw 檔案與抽取 Samples
        raw_p.write_bytes(content)
        extract_samples(raw_p, sample_p, entry["format"], limit=20)

        # 登記 Manifest
        manifest[ds_id] = {
            "name": entry["name"],
            "module_id": entry["module_id"],
            "etag": new_headers.get("etag", prev_etag),
            "last_modified": new_headers.get("last_modified", prev_lm),
            "sha256_hash": new_hash,
            "raw_size": len(content),
            "last_synced_at": datetime.now().isoformat()
        }

        modules_to_update.add(entry["module_id"])
        item_res["status"] = "UPDATED"
        item_res["action"] = "DOWNLOADED_AND_SAMPLED"
        item_res["new_hash"] = new_hash[:10]
        results.append(item_res)

    save_sync_manifest(manifest)

    # 步驟 4: 若有模組需要更新且 auto_etl 為 True，發動補充式增量 ETL
    if auto_etl and modules_to_update:
        target_db, _ = get_fsc_db_path(custom_db)
        sys.stderr.write(f"⚙️ 檢測到 {len(modules_to_update)} 個模組有數據更新，正在執行補充式 ETL 入庫...\n")
        for mod in sorted(modules_to_update):
            etl_res = trigger_incremental_etl(mod, custom_db)
            sys.stderr.write(f"  ✔ [{mod}] 增量 ETL 完成: {etl_res.get('status', 'OK')} (受影響筆數: {etl_res.get('total_records', 0)})\n")

        # 觸發 F00 母大腦倒排全合龍
        try:
            from modules.f00_master_hub.etl import build_f00_master_index
            build_res = build_f00_master_index(target_db)
            sys.stderr.write(f"🌐 母大腦 F00 全域倒排與 360° Profile 已同步重整 (總註冊數: {build_res.get('total_entities_registered')})\n")
        except Exception as e:
            sys.stderr.write(f"⚠️ 母大腦 F00 倒排更新失敗: {e}\n")

    return results

def main():
    parser = argparse.ArgumentParser(description="金管會開放資料同步、週期更新與增量入庫工具 (CGS v2.1)")
    parser.add_argument("--check-updates", action="store_true", help="週期性智慧檢查遠端更新：比對 ETag 與 SHA-256，有變更才下載並補充式增量入庫")
    parser.add_argument("--db", default=None, help="指定目標 SQLite 資料庫路徑 (預設為四階解析路徑)")
    parser.add_argument("--no-etl", action="store_true", help="檢查更新並下載後，不自動觸發模組 ETL")
    parser.add_argument("--sync-all", action="store_true", help="全量下載並抽取前 20 筆樣本")
    parser.add_argument("--extract-only", action="store_true", help="不重新下載，僅從既有 raw 抽取樣本")
    parser.add_argument("--status", action="store_true", help="檢查目前 samples 與 raw 狀態")
    parser.add_argument("-j", "--json", action="store_true", help="輸出 JSON 格式")
    args = parser.parse_args()

    if args.check_updates:
        results = check_and_update_datasets(auto_etl=not args.no_etl, custom_db=args.db)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("📊 週期性資料更新檢測完成：")
            for r in results:
                print(f"  • [{r['module_id']}] {r['name']}: {r['action']}")
    elif args.sync_all:
        results = sync_datasets(download=True, extract=True)
        md_content = generate_datasets_md(results)
        (BASE_DIR / "DATASETS.md").write_text(md_content, encoding="utf-8")
        sys.stderr.write("✅ DATASETS.md 與 samples 已同步生成！\n")
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(f"[{r['module_id']}] {r['name']} ➔ 下載: {r.get('download_status')} | 樣本: {r.get('sample_status')}")
    elif args.extract_only:
        results = sync_datasets(download=False, extract=True)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(f"[{r['module_id']}] {r['name']} ➔ 樣本抽取: {r.get('sample_status')}")
    elif args.status:
        status_list = []
        for entry in DATASET_REGISTRY:
            raw_p = RAW_DIR / entry["local_raw_name"]
            sample_p = SAMPLES_DIR / entry["local_sample_name"]
            status_list.append({
                "module_id": entry["module_id"],
                "name": entry["name"],
                "raw_exists": raw_p.exists(),
                "raw_size": raw_p.stat().st_size if raw_p.exists() else 0,
                "sample_exists": sample_p.exists(),
                "sample_size": sample_p.stat().st_size if sample_p.exists() else 0
            })
        if args.json:
            print(json.dumps(status_list, ensure_ascii=False, indent=2))
        else:
            print("📊 金管會資料庫目前開放資料同步與樣本狀態：")
            for s in status_list:
                r_tag = f"RAW: {s['raw_size']}B" if s["raw_exists"] else "RAW: 缺失"
                s_tag = f"SAMPLE: {s['sample_size']}B" if s["sample_exists"] else "SAMPLE: 缺失"
                print(f"  • [{s['module_id']}] {s['name']}: {r_tag} | {s_tag}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
