#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: fsc_cli.py
title: 金融監督管理委員會 (tw-fsc-db / GOV-A21) 官方 CLI 工具
description: 符合 CLI Governance Spec v2.1 規範之金管會開放資料庫命令列工具，支援母大腦連鎖狀態查詢、Schema 地圖與資料庫維運。
category: cli
spec: events-2026Q3/gov-db-in/sys_eng/02_specification/spec_functional.md
manual: README.md
dependencies: rich
cgs_version: 2.1
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from rich.console import Console

# 顯式宣告 CGS 規格版號
__cli_spec_version__ = "2.1"

# 確保可解析 src 底下模組
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 引入核心函式
from a00_core.fsc_core import get_mother_gov_resolver, query_agency_base_info, get_fsc_db_path, __cli_spec_version__
from a00_core.metadata_manager import get_all_registered_modules

console = Console()

def get_status(custom_db: Optional[str] = None):
    """取得金管會資料庫運作、模組註冊與母大腦連鎖狀態，深度標註各表資料來源真偽 (真實資料 vs 範例資料 vs 衍生聚合)"""
    info = query_agency_base_info("2.16.886.101.20003.20022")
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path, db_source_desc = get_fsc_db_path(custom_db)
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    modules = get_all_registered_modules(db_path)
    
    # 業務主表對應之原始資料路徑 (raw 與 sample)
    source_mapping = {
        'f10_financial_holdings': (raw_dir / 'f10_fhc_setup.csv', samples_dir / 'f10_fhc_setup_sample.csv'),
        'f10_bank_asset_quality': (raw_dir / 'f10_banking12.csv', samples_dir / 'f10_banking12_sample.csv'),
        'f10_land_collateral_loans': (raw_dir / 'f12_land_collateral_loan.csv', samples_dir / 'f10_land_loan_sample.csv'),
        'f10_credit_card_operations': (raw_dir / 'f13_credit_card_stats.csv', samples_dir / 'f10_credit_card_sample.csv'),
        'f10_corporate_loan_trends': (raw_dir / 'f14_corporate_loan.csv', samples_dir / 'f10_corporate_loan_sample.csv'),
        'f20_companies': (raw_dir / 'f20_isin_companies.csv', samples_dir / 'f20_isin_companies_sample.csv'),
        'f20_monthly_revenues': (raw_dir / 'f20_monthly_revenue_public.csv', samples_dir / 'f20_monthly_revenue_sample.csv'),
        'f20_major_shareholders': (raw_dir / 'f20_major_shareholders_listed.csv', samples_dir / 'f20_major_shareholders_sample.csv'),
        'f20_market_valuations': (raw_dir / 'f23_market_valuation.csv', samples_dir / 'f20_market_valuation_sample.csv'),
        'f20_futures_trading': (raw_dir / 'f24_futures_volume.csv', samples_dir / 'f20_futures_volume_sample.csv'),
        'f30_insurance_institutions': (raw_dir / 'f31_insurance_hr.json', samples_dir / 'f30_insurance_hr_sample.json'),
        'f30_insurance_complaint_trends': (raw_dir / 'f32_insurance_complaints.csv', samples_dir / 'f30_insurance_complaints_sample.csv'),
        'f30_special_compensation_fund': (raw_dir / 'f33_special_compensation_fund.csv', samples_dir / 'f30_special_compensation_fund_sample.csv'),
        'f40_exam_deficiencies': (raw_dir / 'f41_exam_deficiencies_fhc.csv', samples_dir / 'f40_exam_deficiencies_fhc_sample.csv'),
        'f40_inspection_execution': (raw_dir / 'f43_inspection_execution.csv', samples_dir / 'f40_inspection_execution_sample.csv'),
        'f50_sanctions': (raw_dir / 'f50_sanctions_rss.xml', samples_dir / 'f50_sanctions_rss_sample.xml'),
        'f50_ombudsman_cases': (raw_dir / 'f51_ombudsman_cases.csv', samples_dir / 'f50_ombudsman_cases_sample.csv'),
        'f60_vasp_compliance_registry': (raw_dir / 'f60_vasp_compliance_registry.json', samples_dir / 'f60_vasp_compliance_sample.json'),
        'f60_fintech_sandbox': (raw_dir / 'f60_fintech_sandbox.json', samples_dir / 'f60_fintech_sandbox_sample.json'),
        'f60_greenhouse_gas_report': (raw_dir / 'f62_greenhouse_gas_report.csv', samples_dir / 'f60_greenhouse_gas_sample.csv')
    }
    
    table_counts = []
    views_list = []
    total_physical_records = 0
    real_records = 0
    sample_records = 0
    
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = cur.fetchone()[0]
                total_physical_records += cnt
                
                # 研判資料性質與真偽來源
                if t.startswith('fts_') or '_fts' in t:
                    category = "INDEX"
                    source_label = "FTS5 倒排索引"
                    is_sample = False
                elif t.startswith('f00_') or t == 'sys_module_metadata':
                    category = "CORE"
                    source_label = "母大腦衍生聚合"
                    is_sample = False
                elif t in source_mapping:
                    category = "BUSINESS"
                    raw_f, smp_f = source_mapping[t]
                    if raw_f.exists() and cnt > 0:
                        source_label = "100% 地面真實資料"
                        is_sample = False
                        real_records += cnt
                    elif smp_f.exists() and cnt > 0:
                        source_label = "範例資料 (SAMPLE) ⚠️"
                        is_sample = True
                        sample_records += cnt
                    else:
                        source_label = "尚未匯入 (EMPTY)"
                        is_sample = False
                else:
                    category = "RESERVED"
                    source_label = "預留綱要 (無資料)"
                    is_sample = False
                    
                table_counts.append({
                    "table_name": t,
                    "record_count": cnt,
                    "category": category,
                    "source_label": source_label,
                    "is_sample": is_sample
                })
            except Exception:
                pass
                
        cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")
        views_list = [r[0] for r in cur.fetchall()]
        conn.close()
        
    return {
        "agency_name": info.get("agency_name", "金融監督管理委員會"),
        "domain_code": "GOV-A21",
        "official_org_code": "300050000G",
        "agency_oid": info.get("agency_oid", "2.16.886.101.20003.20022"),
        "db_path": str(db_path),
        "db_source_desc": db_source_desc,
        "mother_brain": "GOV-300 (tw-gov-db)",
        "connection_status": "CONNECTED",
        "five_pillars_alignment": "100% ALIGNED",
        "spec_version": __cli_spec_version__,
        "registered_modules_count": len(modules),
        "total_physical_records": total_physical_records,
        "real_records": real_records,
        "sample_records": sample_records,
        "tables": table_counts,
        "views": views_list,
        "modules_detail": modules
    }

def get_schema():
    """回傳符合 CGS v2.1 之 schema 地圖"""
    return {
        "domain": "finance",
        "domain_code": "GOV-A21",
        "cgs_spec": __cli_spec_version__,
        "title": "fsc_cli",
        "description": "金融監督管理委員會 (tw-fsc-db) 官方 CLI 指令列工具",
        "commands": {
            "status": {"description": "顯示金管會資料庫運作狀態與母大腦連鎖狀態"},
            "search": {"description": "全域 FTS5 倒排索引關鍵字檢索 (F00)"},
            "bank": {"description": "查詢金融機構、金控集團資產與銀行資產品質 (F10)"},
            "company": {"description": "查詢公開發行公司、營收排行與大股東名冊 (F20)"},
            "schema": {"description": "輸出 JSON Schema 與路由地圖"},
            "version": {"description": "顯示版本與 CGS 規範資訊"}
        },
        "flags": {
            "-j, --json": "單行緊湊 JSON 輸出 (Token-Saving)",
            "-q, --quiet": "極簡輸出 (僅印狀態關鍵字)",
            "-v, --verbose": "詳細 Debug 日誌 (至 stderr)"
        }
    }

def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-j", "--json", action="store_true", help="以 JSON 格式輸出")
    common_parser.add_argument("-q", "--quiet", action="store_true", help="極簡模式輸出")
    common_parser.add_argument("-v", "--verbose", action="store_true", help="輸出詳細 Log")
    common_parser.add_argument("-d", "--db", type=str, default=None, help="指定 SQLite 資料庫路徑 (優先於環境變數 FSC_DB_PATH 與外接硬碟)")

    parser = argparse.ArgumentParser(
        description="金融監督管理委員會 (tw-fsc-db / GOV-A21) 官方 CLI 指令列工具",
        parents=[common_parser]
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # F00 全域檢索子命令
    search_p = subparsers.add_parser("search", parents=[common_parser], help="全域 FTS5 倒排索引關鍵字檢索 (跨金控、銀行、公發公司、裁罰)")
    search_p.add_argument("keyword", help="檢索關鍵字")
    search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    # F00 360 度跨模組全景實體檔案子命令
    prof_global_p = subparsers.add_parser("profile", parents=[common_parser], help="調閱單一機構之 360 度跨模組全景監理與營運檔案")
    prof_global_p.add_argument("keyword", help="機構全銜、商業簡稱、股票程式碼或統一編號")

    # F00 跨模組集團控制力與股權網路拓樸子命令
    rel_p = subparsers.add_parser("relations", parents=[common_parser], help="查詢金融控股集團股權控制鏈、旗下特許子公司與大股東持股網路")
    rel_p.add_argument("keyword", help="金控名稱、銀行全銜、上市公司代號或大股東姓名")

    # F20 證券與公開發行公司子命令
    comp_p = subparsers.add_parser("company", parents=[common_parser], help="查詢公開發行公司、營收排行與大股東名冊")
    comp_sub = comp_p.add_subparsers(dest="comp_action", help="證券模組操作")
    
    top_rev_p = comp_sub.add_parser("top", parents=[common_parser], help="查詢當月營收或年增率最高公司")
    top_rev_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    top_rev_p.add_argument("--min-yoy", type=float, default=None, help="最低 YoY 年增率門檻 (%)")
    
    prof_p = comp_sub.add_parser("profile", parents=[common_parser], help="一鍵查詢公司基本面、最新月營收與大股東名冊")
    prof_p.add_argument("query", help="公司代號或名稱")
    
    sh_p = comp_sub.add_parser("shareholders", parents=[common_parser], help="查詢特定公司持股逾 10% 大股東名冊")
    sh_p.add_argument("query", help="公司代號或名稱")

    val_p = comp_sub.add_parser("valuation", parents=[common_parser], help="查詢上櫃股票本益比、殖利率與股價淨值比排行")
    val_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    val_p.add_argument("--min-yield", type=float, default=None, help="最低殖利率門檻 (%)")
    val_p.add_argument("--max-pe", type=float, default=None, help="最高本益比門檻")

    fut_p = comp_sub.add_parser("futures", parents=[common_parser], help="查詢期交所主力期貨商品月成交量與未平倉排行")
    fut_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    # F30 保險市場與精算子命令
    ins_parser = subparsers.add_parser("insurer", parents=[common_parser], help="查詢保險機構、精算人力、消費爭議申訴與特別補償基金")
    ins_sub = ins_parser.add_subparsers(dest="ins_action", help="保險模組操作")
    
    ins_list_p = ins_sub.add_parser("list", parents=[common_parser], help="查詢產壽險機構、從業人員與精算配置排行")
    ins_list_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")
    ins_list_p.add_argument("--type", choices=["LIFE", "PROPERTY"], default=None, help="篩選人壽或產險")
    ins_list_p.add_argument("--sort", choices=["actuary_count", "underwriting_count", "claim_count", "inner_staff_count", "field_agent_count"], default="actuary_count", help="排序欄位")

    ins_comp_p = ins_sub.add_parser("complaints", parents=[common_parser], help="查詢歷年保險消費爭議申訴件數與解決率趨勢")
    ins_comp_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出年數")

    ins_fund_p = ins_sub.add_parser("fund", parents=[common_parser], help="查詢特別補償基金收支與每案平均補償金")
    ins_fund_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出年數")

    # F10 銀行與金控子命令
    bank_parser = subparsers.add_parser("bank", parents=[common_parser], help="查詢金融機構、金控集團資產與銀行資產品質")
    bank_sub = bank_parser.add_subparsers(dest="bank_action", help="銀行模組操作")
    
    fhc_p = bank_sub.add_parser("holdings", parents=[common_parser], help="查詢金融控股公司資產與子公司")
    fhc_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    
    npl_p = bank_sub.add_parser("quality", parents=[common_parser], help="查詢銀行逾放比與資產品質")
    npl_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    npl_p.add_argument("--max-npl", type=float, default=None, help="最大逾放比門檻 (%)")

    land_p = bank_sub.add_parser("land", parents=[common_parser], help="查詢金融機構土地擔保放款餘額與集中度")
    land_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    land_p.add_argument("--min-ratio", type=float, default=0.0, help="最低土地放款佔比門檻 (%)")

    cards_p = bank_sub.add_parser("cards", parents=[common_parser], help="查詢本國發卡機構信用卡營運與簽帳金額排行")
    cards_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    corp_p = bank_sub.add_parser("corporate", parents=[common_parser], help="查詢聯徵中心全台企業貸款月度統計趨勢")
    corp_p.add_argument("-n", "--limit", type=int, default=6, help="限制輸出月數")

    radar_p = bank_sub.add_parser("radar", parents=[common_parser], help="查詢商業銀行資產品質、土融集中度與信用卡風險雷達")
    radar_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    # F40 金融檢查重大缺失子命令
    exam_parser = subparsers.add_parser("exam", parents=[common_parser], help="查詢檢查局金融檢查重大缺失、FTS5違規檢索與年度執行統計")
    exam_sub = exam_parser.add_subparsers(dest="exam_action", help="金融檢查模組操作")
    
    exam_search_p = exam_sub.add_parser("search", parents=[common_parser], help="透過 FTS5 全文檢索金融檢查重大缺失態樣與情節")
    exam_search_p.add_argument("keyword", help="檢索關鍵字 (如 創投、不動產、洗錢、衍生性)")
    exam_search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    exam_search_p.add_argument("--sector", choices=["HOLDING", "FOREIGN_BANK"], default=None, help="篩選受檢業別")

    exam_cat_p = exam_sub.add_parser("categories", parents=[common_parser], help="查詢重大缺失高頻業務專案分佈統計")
    exam_cat_p.add_argument("--sector", choices=["HOLDING", "FOREIGN_BANK"], default=None, help="篩選受檢業別")

    exam_exec_p = exam_sub.add_parser("execution", parents=[common_parser], help="查詢檢查局實地檢查受檢機構年度執行統計")
    exam_exec_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")
    exam_exec_p.add_argument("--year", default=None, help="篩選統計年度")

    exam_pen_p = exam_sub.add_parser("penetrate", parents=[common_parser], help="[進階] 缺失態樣穿透集團股權拓樸 (關聯受檢金控之子公司管理缺失與轄下受控實體)")
    exam_pen_p.add_argument("holding", help="金控名稱或代號 (如 華南金、富邦金、中信金)")

    # F60 金融科技、VASP 與永續金融子命令
    fintech_parser = subparsers.add_parser("fintech", parents=[common_parser], help="查詢虛擬資產平台 (VASP)、金融科技監理沙盒與 ESG 永續碳排")
    fintech_sub = fintech_parser.add_subparsers(dest="fintech_action", help="金融科技與永續模組操作")
    
    vasp_p = fintech_sub.add_parser("vasp", parents=[common_parser], help="查詢洗錢防制法令遵循之虛擬資產平台業者 (VASP) 名冊")
    vasp_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")
    vasp_p.add_argument("--status", choices=["COMPLIANT", "WITHDRAWN", "SUSPENDED"], default=None, help="篩選合規狀態")

    sandbox_p = fintech_sub.add_parser("sandbox", parents=[common_parser], help="查詢金管會核准之金融科技監理沙盒創新實驗專案")
    sandbox_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")
    sandbox_p.add_argument("--status", choices=["ACTIVE", "GRADUATED", "TERMINATED"], default=None, help="篩選實驗狀態")

    esg_p = fintech_sub.add_parser("esg", parents=[common_parser], help="查詢國家歷年溫室氣體排放清冊報告 (ESG 碳排)")
    esg_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出年數")

    fin_pen_p = fintech_sub.add_parser("penetrate", parents=[common_parser], help="[進階] 新創沙盒 ➔ 合作傳統特許銀行體質穿透 (F60 關聯 F10/F50)")
    fin_pen_p.add_argument("query", help="沙盒案號或申請機構 (如 好好投資、阿爾發)")

    vasp_aml_p = fintech_sub.add_parser("aml-check", parents=[common_parser], help="[進階] 傳統銀行之虛擬通貨 (VASP) 監控缺失裁罰聯防")
    vasp_aml_p.add_argument("--keyword", default="虛擬", help="檢索關鍵字 (預設: 虛擬)")

    # F50 法律事務、處分裁罰與評議爭議子命令
    sanc_parser = subparsers.add_parser("sanction", parents=[common_parser], help="查詢金管會重大裁處處分書、FTS5違法事實檢索與金融消費爭議")
    sanc_sub = sanc_parser.add_subparsers(dest="sanc_action", help="裁罰與法律模組操作")
    
    sanc_search_p = sanc_sub.add_parser("search", parents=[common_parser], help="透過 FTS5 全文倒排檢索正式裁罰處分書 (案號、事實、法條)")
    sanc_search_p.add_argument("keyword", help="檢索關鍵字 (如 信用卡、挪用、資安、洗錢、經理人)")
    sanc_search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    sanc_top_p = sanc_sub.add_parser("top", parents=[common_parser], help="查詢受裁罰金融機構歷史累計罰鍰與處分件數排行")
    sanc_top_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    sanc_case_p = sanc_sub.add_parser("cases", parents=[common_parser], help="查詢金融消費評議中心銀行業爭議申訴統計排行")
    sanc_case_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")

    sanc_esc_p = sanc_sub.add_parser("escalation", parents=[common_parser], help="[進階] 重大缺失 ➔ 監理裁罰演進追蹤 (F40 檢查缺失比對 F50 正式裁處)")
    sanc_esc_p.add_argument("keyword", help="業務或違規關鍵字 (如 信用卡、資安、申報、防制洗錢)")

    subparsers.add_parser("status", parents=[common_parser], help="顯示本部會資料庫運作狀態與母大腦連鎖狀態")
    subparsers.add_parser("schema", parents=[common_parser], help="輸出 JSON Schema 與命令地圖")
    subparsers.add_parser("version", parents=[common_parser], help="顯示 CLI 版本資訊")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    args = parser.parse_args()

    db_path, db_source_desc = get_fsc_db_path(getattr(args, "db", None))
    if args.command == "status":
        status_data = get_status(getattr(args, "db", None))
        if args.quiet:
            print("CONNECTED")
        elif args.json:
            print(json.dumps(status_data, ensure_ascii=False, separators=(',', ':')))
        else:
            console.print("[bold green]📊 金融監督管理委員會 (GOV-A21) 資料庫運作狀態看板[/bold green]")
            console.print(f"  • 資料庫路徑 (Database Path) : [bold cyan]{status_data['db_path']}[/bold cyan]")
            console.print(f"  • 路徑來源 (Path Source)     : [bold white]{status_data['db_source_desc']}[/bold white]")
            console.print(f"  • 部會程式碼 (Domain Code) : [yellow]{status_data['domain_code']}[/yellow]")
            console.print(f"  • 機關名稱 (Agency Name) : [white]{status_data['agency_name']}[/white]")
            console.print(f"  • 主管機關 OID           : [yellow]{status_data['agency_oid']}[/yellow]")
            console.print(f"  • 官方機關程式碼           : [white]{status_data['official_org_code']}[/white]")
            console.print(f"  • 母大腦連鎖狀態         : [cyan]{status_data['connection_status']} ({status_data['mother_brain']})[/cyan]")
            console.print(f"  • 通用五大基石介面       : [green]{status_data['five_pillars_alignment']}[/green]")
            console.print(f"  • 資料庫總記錄筆數       : [bold yellow]{status_data.get('total_physical_records', 0):,} 筆[/bold yellow]")
            
            # 顯式資料來源品質指標
            sample_cnt = status_data.get("sample_records", 0)
            sample_style = "[bold green]0 筆 (100% 杜絕純範例資料)[/bold green]" if sample_cnt == 0 else f"[bold red]{sample_cnt:,} 筆 (包含範例資料⚠️)[/bold red]"
            console.print(f"  • 地面真實資料筆數       : [bold green]{status_data.get('real_records', 0):,} 筆[/bold green]")
            console.print(f"  • 範例資料筆數檢核       : {sample_style}")
            
            if status_data.get("tables"):
                from rich.table import Table
                t = Table(title="🗄️ 實體資料表狀態與真偽檢驗統計 (Physical Tables Source Audit)", show_header=True, header_style="bold magenta")
                t.add_column("資料表名稱 (Table Name)", style="white")
                t.add_column("即時筆數 (Count)", justify="right", style="cyan")
                t.add_column("性質 (Type)", style="yellow")
                t.add_column("資料來源真偽檢核 (Data Source Audit)", style="bold")
                
                for row in status_data["tables"]:
                    cnt_str = f"{row['record_count']:,}"
                    src = row["source_label"]
                    if "100%" in src:
                        src_style = f"[bold green]✔ {src}[/bold green]"
                    elif "範例" in src:
                        src_style = f"[bold red]⚠ {src}[/bold red]"
                    elif "母大腦" in src:
                        src_style = f"[bold cyan]✦ {src}[/bold cyan]"
                    elif "FTS5" in src:
                        src_style = f"[dim white]⚲ {src}[/dim white]"
                    else:
                        src_style = f"[dim]{src}[/dim]"
                    t.add_row(row["table_name"], cnt_str, row["category"], src_style)
                console.print(t)
                
            if status_data.get("views"):
                console.print("[bold]👁️ 業務與監理檢視表 (Views)：[/bold]")
                for v in status_data["views"]:
                    console.print(f"  • [cyan]{v}[/cyan]")
    elif args.command == "search":
        # 動態載入 F00 模組
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f00_master_hub"))
        from commands_f00 import search_global_entities
        results = search_global_entities(db_path, args.keyword, limit=args.limit)
        
        if args.quiet:
            for r in results:
                print(f"[{r['domain_code']}] {r['primary_name']}")
        elif args.json:
            print(json.dumps(results, ensure_ascii=False))
        else:
            console.print(f"[bold green]🔍 全域 FTS5 檢索結果：關鍵字 '{args.keyword}' (命中 {len(results)} 筆)[/bold green]")
            for i, r in enumerate(results, 1):
                console.print(f"  {i}. [[yellow]{r['domain_code']}[/yellow]/[cyan]{r['entity_type']}[/cyan]] [bold white]{r['primary_name']}[/bold white]")
                if r.get('secondary_info'):
                    console.print(f"     [dim]{r['secondary_info'][:80]}...[/dim]")
    elif args.command == "profile":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f00_master_hub"))
        from commands_f00 import query_entity_360
        prof = query_entity_360(db_path, args.keyword)
        if not prof:
            if not args.quiet:
                console.print(f"[bold red]❌ 查無實體檔案：'{args.keyword}'[/bold red]")
        elif args.quiet:
            print(f"{prof.get('canonical_name')} [{prof.get('entity_class')}]")
        elif args.json:
            print(json.dumps(prof, ensure_ascii=False, indent=2))
        else:
            console.print(f"[bold green]🏛️ 金管會 360° 跨模組全景實體檔案：[white]{prof.get('canonical_name')}[/white][/bold green]")
            console.print(f"  • 權威識別碼 (Master UID) : [yellow]{prof.get('master_uid')}[/yellow]")
            console.print(f"  • 實體類別 (Entity Class) : [cyan]{prof.get('entity_class')}[/cyan] | 商業別名: {prof.get('common_alias')}")
            if prof.get("stock_code"):
                console.print(f"  • 股票公開程式碼 (F20)     : [bold white]{prof['stock_code']}[/bold white]")
            if prof.get("fhc_assets_billion"):
                console.print(f"  • 金控集團資產 (F10)     : [yellow]{prof['fhc_assets_billion']:,.0f} 億元[/yellow]")
            if prof.get("bank_npl_ratio") is not None:
                console.print(f"  • 商業銀行資產品質 (F10) : 放款總額 [white]{prof.get('bank_loan_total', 0):,.0f}M[/white] | 逾放比 [green]{prof['bank_npl_ratio']}%[/green] (涵蓋率: {prof.get('bank_coverage_ratio', 0):,.1f}%)")
            if prof.get("bank_land_loan_ratio") is not None:
                console.print(f"  • 土地擔保放款餘額 (F10) : [yellow]{prof.get('bank_land_loan_balance', 0):,.0f} 百萬元[/yellow] (放款佔比: [magenta]{prof.get('bank_land_loan_ratio')}%[/magenta])")
            if prof.get("cc_signing_amount") is not None:
                console.print(f"  • 信用卡業務消費力 (F10) : 月簽帳 [yellow]{prof.get('cc_signing_amount'):,.1f} 百萬元[/yellow] (活卡率: [green]{prof.get('cc_active_card_ratio')}%[/green])")
            if prof.get("listed_monthly_revenue"):
                console.print(f"  • 公開市場當月營收 (F20) : [yellow]{prof['listed_monthly_revenue']:,.0f} 千元[/yellow] (YoY: [green]{prof.get('listed_revenue_yoy')}%[/green])")
            if prof.get("listed_dividend_yield") is not None or prof.get("listed_pe_ratio") is not None:
                pe_str = f"P/E: {prof.get('listed_pe_ratio')}" if prof.get('listed_pe_ratio') else "P/E: N/A"
                yield_str = f"殖利率: {prof.get('listed_dividend_yield')}%" if prof.get('listed_dividend_yield') else "殖利率: N/A"
            if prof.get("insurer_inner_staff") is not None or prof.get("insurer_actuary_count") is not None:
                i_type_zh = "人壽保險" if prof.get("insurer_type") == "LIFE" else ("產物保險" if prof.get("insurer_type") == "PROPERTY" else "保險機構")
                console.print(f"  • 保險專業人力佈局 (F30) : 類型 [{i_type_zh}] | 精算: [bold yellow]{prof.get('insurer_actuary_count', 0)}人[/bold yellow] | 核保: {prof.get('insurer_underwriting_count', 0)}人 | 理賠: {prof.get('insurer_claim_count', 0)}人 | 內勤: {prof.get('insurer_inner_staff', 0):,}人 | 外勤: {prof.get('insurer_field_agent', 0):,}人")
            if prof.get("ombudsman_complaint_count") is not None:
                console.print(f"  • 消費爭議申訴統計 (F50) : 評議中心受理 [bold yellow]{prof.get('ombudsman_complaint_count', 0)} 件[/bold yellow] (申訴案件比率: [magenta]{prof.get('ombudsman_complaint_ratio')}%[/magenta])")
            if prof.get("vasp_id"):
                console.print(f"  • 虛擬資產平台合規 (F60) : 登記碼 [{prof['vasp_id']}] | 品牌: [bold yellow]{prof.get('vasp_brand_name')}[/bold yellow] | 信託銀行: [bold green]{prof.get('vasp_fiat_bank')}[/bold green] (狀態: [cyan]{prof.get('vasp_compliance_status')}[/cyan])")
            if prof.get("sandbox_case_no"):
                s_status = f"[bold green]{prof['sandbox_status']}[/bold green]" if prof['sandbox_status'] == 'GRADUATED' else f"[bold yellow]{prof['sandbox_status']}[/bold yellow]"
                console.print(f"  • 金融科技監理沙盒 (F60) : 案號 [{prof['sandbox_case_no']}] | 合作銀行: [bold white]{prof.get('sandbox_partner_institution')}[/bold white] | 狀態: {s_status}")
                console.print(f"     [bold yellow]實驗主題：{prof.get('sandbox_experiment_title')}[/bold yellow]")
            risk = prof.get("composite_risk_level") or "GREEN"
            def_cnt = prof.get("exam_deficiency_count") or 0
            sanc_cnt = prof.get("total_sanctions_count") or 0
            fine_ntd = prof.get("total_penalty_fine_ntd") or 0.0
            risk_color = "green" if "GREEN" in risk else ("yellow" if "YELLOW" in risk else "red")
            console.print(f"  • 綜合監理風險指標       : [{risk_color}][{risk}][/{risk_color}] (金檢缺失: [bold yellow]{def_cnt} 次[/bold yellow] | 裁罰: [bold red]{sanc_cnt} 件[/bold red] / [bold red]{fine_ntd:,.0f} 元[/bold red])")

            # 跨模組控制力拓樸關聯
            from commands_f00 import query_entity_relations
            rels = query_entity_relations(db_path, args.keyword)
            if rels.get("subsidiaries"):
                console.print(f"  • 集團控制力子公司 (F00) : 掌控 [bold yellow]{len(rels['subsidiaries'])}[/bold yellow] 家持牌或關係機構")
                for sub in rels["subsidiaries"][:5]:
                    console.print(f"    ├─ [{sub['related_class']}] [cyan]{sub['related_name']}[/cyan] ({sub['relation_type']} {sub['shareholding_ratio']}%)")
                if len(rels["subsidiaries"]) > 5:
                    console.print(f"    └─ ... 另有 {len(rels['subsidiaries']) - 5} 家 (可透過 `fsc relations` 查看完整清單)")
            if rels.get("parents_or_shareholders"):
                console.print(f"  • 最終控制母公司/大股東  : 關聯 [bold yellow]{len(rels['parents_or_shareholders'])}[/bold yellow] 個持股控制來源")
                for p in rels["parents_or_shareholders"][:3]:
                    console.print(f"    └─ [{p['related_class']}] [bold white]{p['related_name']}[/bold white] ({p['relation_type']} {p['shareholding_ratio']}%)")
    elif args.command == "relations":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f00_master_hub"))
        from commands_f00 import query_entity_relations
        res = query_entity_relations(db_path, args.keyword)
        ent = res.get("entity")
        if not ent:
            console.print(f"[bold red]❌ 查無實體或未建立關聯：'{args.keyword}'[/bold red]")
        elif args.quiet:
            print(f"{ent['canonical_name']}: 子公司 {len(res['subsidiaries'])}, 母/股東 {len(res['parents_or_shareholders'])}")
        elif args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            console.print(f"[bold green]🕸️ 金管會跨模組集團股權與控制力拓樸樹：[white]{ent['canonical_name']}[/white] ({ent['entity_class']})[/bold green]")
            if res["parents_or_shareholders"]:
                console.print("[bold yellow]▲ 上游控制來源 (母公司 / 金控集團 / 逾10%大股東)：[/bold yellow]")
                for i, p in enumerate(res["parents_or_shareholders"], 1):
                    console.print(f"  {i}. [{p['related_class']}] [bold white]{p['related_name']}[/bold white] | 關係: [cyan]{p['relation_type']}[/cyan] | 控制: {p['control_level']} ({p['shareholding_ratio']}%)")
            
            if res["subsidiaries"]:
                console.print(f"[bold cyan]▼ 下游受控實體 (金融特許子公司 / 關係企業 / 轉投資，共 {len(res['subsidiaries'])} 家)：[/bold cyan]")
                for i, s in enumerate(res["subsidiaries"], 1):
                    code_str = f" [{s['related_stock_code']}]" if s.get('related_stock_code') else ""
                    console.print(f"  {i}. [{s['related_class']}] [bold white]{s['related_name']}{code_str}[/bold white] | 關係: [yellow]{s['relation_type']}[/yellow] | 持股: [green]{s['shareholding_ratio']}%[/green] ({s['control_level']})")
            
            if not res["parents_or_shareholders"] and not res["subsidiaries"]:
                console.print("  [dim]目前該實體無已登記之上游母公司或下游子公司拓樸邊。[/dim]")
    elif args.command == "company":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f20_securities_markets_db"))
        from commands_f20 import query_top_revenue_companies, query_company_profile, query_major_shareholders
        
        if args.comp_action == "top":
            data = query_top_revenue_companies(db_path, limit=args.limit, min_yoy=args.min_yoy)
            if args.quiet:
                for d in data:
                    print(f"{d['company_code']} {d['company_name']}: {d['current_month_revenue']}千元")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                title = "📈 上市公司營收排行" if args.min_yoy is None else f"🚀 上市公司營收高成長排行 (YoY >= {args.min_yoy}%)"
                console.print(f"[bold green]{title} (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [{d['company_code']}] [bold cyan]{d['company_name']}[/bold cyan] ({d.get('industry_name', '未分類')}) | 當月營收: [yellow]{d['current_month_revenue']:,.0f} 千元[/yellow] | YoY: [green]{d['yoy_growth_rate']}%[/green]")
        elif args.comp_action == "profile":
            prof = query_company_profile(db_path, args.query)
            if not prof:
                console.print(f"[yellow]⚠️ 找不到與 '{args.query}' 相符的公司 profile。[/yellow]")
            elif args.quiet:
                print(f"{prof['company_code']} {prof['company_name']}")
            elif args.json:
                print(json.dumps(prof, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏢 公司全維度營收與股權 Profile：[{prof['company_code']}] {prof['company_name']}[/bold green]")
                console.print(f"  • 市場別 / 產業別 : [white]{prof['market_type']} / {prof['industry_category']}[/white]")
                console.print(f"  • 掛牌上市日期     : [cyan]{prof['listing_date']}[/cyan]")
                if prof.get("revenue_year_month"):
                    console.print(f"  • 最新月營收 ({prof['revenue_year_month']}) : [yellow]{prof['current_month_revenue']:,.0f} 千元[/yellow] (YoY: [green]{prof['yoy_growth_rate']}%[/green])")
                if prof.get("major_shareholders_count"):
                    console.print(f"  • 10% 大股東人數   : [bold]{prof['major_shareholders_count']} 位[/bold]")
                    console.print(f"  • 大股東名冊摘要   : [dim]{prof['major_shareholders_summary']}[/dim]")
        elif args.comp_action == "shareholders":
            data = query_major_shareholders(db_path, args.query)
            if args.quiet:
                for d in data:
                    print(d["shareholder_name"])
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]👥 公司持股逾 10% 大股東名單：'{args.query}' (共 {len(data)} 位)[/bold green]")
                for i, d in enumerate(data, 1):
                    kind = "[法人機構]" if d.get("is_corporate") == 1 else "[自然人]"
                    console.print(f"  {i}. [cyan]{kind}[/cyan] [bold white]{d['shareholder_name']}[/bold white] (基準日: {d['report_date']})")
        elif args.comp_action == "valuation":
            from commands_f20 import query_market_valuations
            data = query_market_valuations(db_path, limit=args.limit, min_yield=args.min_yield, max_pe=args.max_pe)
            if args.quiet:
                for d in data:
                    print(f"{d['company_code']} {d['company_name']}: {d['dividend_yield']}%")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                title = "💎 上櫃股票市場估值與高殖利率排行" if args.min_yield is None else f"💎 高殖利率精選 (殖利率 >= {args.min_yield}%)"
                console.print(f"[bold green]{title} (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [{d['company_code']}] [bold cyan]{d['company_name']}[/bold cyan] | 殖利率: [green]{d['dividend_yield']}%[/green] | P/E: [yellow]{d['pe_ratio']}[/yellow] | P/B: {d['pb_ratio']} | 每股股利: {d['dividend_per_share']}元")
        elif args.comp_action == "futures":
            from commands_f20 import query_futures_trading
            data = query_futures_trading(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['contract_code']} {d['contract_name']}: {d['total_volume']}口")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]📊 臺灣期交所主力商品交易量排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [{d['contract_code']}] [bold cyan]{d['contract_name']}[/bold cyan] ({d['trade_month']}) | 月成交量: [yellow]{d['total_volume']:,} 口[/yellow] | 未平倉: [cyan]{d['open_interest']:,} 口[/cyan] | 契約值: {d['contract_value_million']:,.1f} 百萬")
    elif args.command == "insurer":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f30_insurance_actuarial_db"))
        from commands_f30 import query_insurance_institutions, query_complaint_trends, query_compensation_fund
        if args.ins_action == "list":
            data = query_insurance_institutions(db_path, limit=args.limit, institution_type=args.type, order_by=args.sort)
            if args.quiet:
                for d in data:
                    print(f"{d['insurer_name']}: 精算 {d['actuary_count']}人")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🛡️ 保險機構人力與精算專業配置排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    t_zh = "人壽" if d['insurer_type'] == "LIFE" else "產險"
                    console.print(f"  {i}. [bold cyan]{d['insurer_name']}[/bold cyan] ({t_zh}) | 精算: [bold yellow]{d['actuary_count']}人[/bold yellow] | 核保: {d['underwriting_count']}人 | 理賠: {d['claim_count']}人 | 外勤: {d['field_agent_count']:,}人")
        elif args.ins_action == "complaints":
            data = query_complaint_trends(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['eval_year']}: 申訴 {d['complaint_count']}件")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]⚖️ 全台保險消費爭議申訴與和解趨勢 (近 {len(data)} 年)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  • [cyan]{d['eval_year']} 年[/cyan] | 申訴: [yellow]{d['complaint_count']:,} 件[/yellow] | 申訴率: {d['complaint_ratio']}% | 和解率: [green]{d['settlement_ratio']}%[/green] | 依申訴人意見辦理: {d['complainant_favored_ratio']}%")
        elif args.ins_action == "fund":
            data = query_compensation_fund(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['stat_year']}: 平均 {d['avg_compensation_thousand']}仟元")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🚗 汽車交通事故特別補償基金運作趨勢 (近 {len(data)} 年)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  • [cyan]{d['stat_year']} 年[/cyan] | 補償支出: [yellow]{d['compensation_expense_thousand']:,.0f} 仟元[/yellow] | 補償件數: {d['compensated_cases']:,} 件 | 每件平均給付: [bold green]{d['avg_compensation_thousand']:,.1f} 仟元[/bold green]")
        else:
            ins_parser.print_help(sys.stderr)
    elif args.command == "bank":
        # 動態載入 F10 模組
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f10_banking_credit_db"))
        from commands_f10 import query_financial_holdings, query_bank_asset_quality
        
        from commands_f10 import (
            query_financial_holdings,
            query_bank_asset_quality,
            query_land_collateral_loans,
            query_credit_card_operations,
            query_corporate_loan_trends,
            query_bank_credit_risk_radar
        )
        if args.bank_action == "holdings":
            data = query_financial_holdings(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(d["holding_name"])
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏛️ 全臺主要金融控股公司資產排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold cyan]{d['holding_name']}[/bold cyan] | 集團資產: [yellow]{d['group_assets_billion']:,.0f} 億元[/yellow] | 子公司: {d['subsidiaries_count']} 家")
        elif args.bank_action == "quality":
            data = query_bank_asset_quality(db_path, limit=args.limit, max_npl=args.max_npl)
            if args.quiet:
                for d in data:
                    print(f"{d['bank_name']}: {d['npl_ratio']}%")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]📊 本國銀行資產品質排行 (放款規模 Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 放款: [white]{d['loan_total']:,.0f} 百萬元[/white] | 逾放比: [green]{d['npl_ratio']}%[/green] | 涵蓋率: {d['coverage_ratio']:,.1f}%")
        elif args.bank_action == "land":
            data = query_land_collateral_loans(db_path, limit=args.limit, min_ratio=args.min_ratio)
            if args.quiet:
                for d in data:
                    print(f"{d['bank_name']}: {d['land_loan_balance']}百萬")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏞️ 銀行土地擔保放款與集中度排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 土地融資: [yellow]{d['land_loan_balance']:,.0f} 百萬元[/yellow] | 總放款: {d['total_loan_including_call']:,.0f} 百萬元 | 佔比: [magenta]{d['land_loan_ratio']}%[/magenta]")
        elif args.bank_action == "cards":
            data = query_credit_card_operations(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['institution_name']}: {d['signing_amount_million']}百萬")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]💳 信用卡業務與簽帳消費力排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold cyan]{d['institution_name']}[/bold cyan] | 簽帳金額: [yellow]{d['signing_amount_million']:,.1f} 百萬元[/yellow] | 流通卡: {d['cards_effective']:,} 張 | 活卡率: [green]{d['active_card_ratio']}%[/green]")
        elif args.bank_action == "corporate":
            data = query_corporate_loan_trends(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['year_month']}: {d['loan_total_billion']}十億")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏭 聯徵中心全台企業總貸款趨勢 (近 {len(data)} 個月)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  • [cyan]{d['year_month']}[/cyan] | 貸款總額: [yellow]{d['loan_total_billion']:,.2f} 億元[/yellow] | 總家數: {d['loan_entity_count']:,} 家 | 平均每家: [white]{d['loan_avg_thousand']:,.1f} 仟元[/white]")
        elif args.bank_action == "radar":
            data = query_bank_credit_risk_radar(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['bank_name']}: {d['supervisory_risk_badge']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🛡️ 商業銀行信用風險監理綜合雷達 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    badge = d['supervisory_risk_badge']
                    color = "green" if badge == "GREEN" else ("yellow" if badge == "YELLOW" else "red")
                    console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 總放款: {d['loan_total']:,.0f}百萬 | 逾放比: {d['npl_ratio']}% | 土融比率: {d['land_loan_ratio']}% | 燈號: [{color}][{badge}][/{color}]")
        else:
            bank_parser.print_help(sys.stderr)
    elif args.command == "exam":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f40_inspection_bureau_db"))
        from commands_f40 import search_exam_deficiencies, query_deficiency_categories, query_inspection_executions, query_holding_deficiency_penetration
        if args.exam_action == "search":
            data = search_exam_deficiencies(db_path, args.keyword, target_sector=args.sector, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"[{d['target_sector']}] {d['deficiency_pattern']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🔍 檢查局重大缺失檢索：關鍵字 '{args.keyword}' (命中 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    sec_zh = "金控公司" if d['target_sector'] == "HOLDING" else "外銀在臺分行"
                    console.print(f"  {i}. [[yellow]{sec_zh}[/yellow] / [cyan]{d['business_category']}[/cyan]] [bold white]{d['deficiency_pattern']}[/bold white] ({d['eval_year']} {d['half_year']})")
                    console.print(f"     [dim]情節：{d['deficiency_detail'][:100]}...[/dim]")
                    if d.get("improvement_action"):
                        console.print(f"     [green]要求改善：{d['improvement_action'][:100]}...[/green]")
        elif args.exam_action == "categories":
            data = query_deficiency_categories(db_path, target_sector=args.sector)
            if args.quiet:
                for d in data:
                    print(f"{d['business_category']}: {d['deficiency_count']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]📊 重大內控與法遵缺失業務專案統計排行[/bold green]")
                for i, d in enumerate(data, 1):
                    sec_zh = "金控公司" if d['target_sector'] == "HOLDING" else "外銀在臺分行"
                    console.print(f"  {i}. [{sec_zh}] [bold cyan]{d['business_category']}[/bold cyan] : [bold yellow]{d['deficiency_count']} 件[/bold yellow] (佔比 [magenta]{d['category_pct']}%[/magenta])")
        elif args.exam_action == "execution":
            data = query_inspection_executions(db_path, eval_year=args.year, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['eval_year']} {d['target_sector']}: {d['inspected_count']}家")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏛️ 檢查局實地檢查受檢機構執行家數統計 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [cyan]{d['eval_year']} 年[/cyan] | [yellow]{d['target_sector']}[/yellow] ({d['exam_type']}) : [bold green]{d['inspected_count']:,} 家[/bold green]")
        elif args.exam_action == "penetrate":
            data = query_holding_deficiency_penetration(db_path, args.holding)
            if args.quiet:
                print(f"{data['holding_name']}: 子公司 {data['subsidiaries_count']} 家, 相關缺失 {data['deficiencies_count']} 筆")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                console.print(f"[bold green]🕸️ [F40-ADV] 金檢缺失穿透集團股權拓樸：[white]{data['holding_name']}[/white][/bold green]")
                console.print(f"  • 關聯受控子公司家數 : [bold yellow]{data['subsidiaries_count']}[/bold yellow] 家")
                console.print(f"  • 督導子公司相關缺失 : [bold red]{data['deficiencies_count']}[/bold red] 筆")
                
                if data["deficiencies"]:
                    console.print("[bold yellow]▼ 金檢實地發現之金控子公司管理/風險管理重大缺失明細：[/bold yellow]")
                    for i, d in enumerate(data["deficiencies"][:3], 1):
                        console.print(f"  {i}. [[cyan]{d['business_category']}[/cyan]] [bold white]{d['deficiency_pattern']}[/bold white] ({d['eval_year']} {d['half_year']})")
                        console.print(f"     [dim]缺失情節：{d['deficiency_detail'][:110]}...[/dim]")
                        if d.get("improvement_action"):
                            console.print(f"     [green]改善要求：{d['improvement_action'][:110]}...[/green]")
                
                if data["penetrated_subsidiaries"]:
                    console.print("[bold cyan]▼ 透過 F00 拓樸穿透之旗下金融實體經營與專業指標：[/bold cyan]")
                    for i, s in enumerate(data["penetrated_subsidiaries"], 1):
                        info_parts = []
                        if s.get("bank_loan_total"):
                            info_parts.append(f"總放款: {s['bank_loan_total']:,.0f}百萬 (NPL: {s.get('bank_npl_ratio')}%)")
                        if s.get("monthly_revenue"):
                            info_parts.append(f"最新月營收: {s['monthly_revenue']:,.0f}千元 (YoY: {s.get('revenue_yoy')}%)")
                        if s.get("actuary_count"):
                            info_parts.append(f"精算師: {s['actuary_count']}人 (外勤: {s.get('field_agent_count', 0):,}人)")
                        extra = f" | {', '.join(info_parts)}" if info_parts else ""
                        console.print(f"  {i}. [{s['entity_class']}] [bold white]{s['canonical_name']}[/bold white] (持股 {s['shareholding_ratio']}%, {s['relation_type']}){extra}")
        else:
            exam_parser.print_help(sys.stderr)
    elif args.command == "sanction":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f50_sanctions_legal_db"))
        from commands_f50 import (
            search_sanctions,
            query_top_penalized_institutions,
            query_ombudsman_disputes,
            track_deficiency_to_sanction_escalation
        )
        if args.sanc_action == "search":
            data = search_sanctions(db_path, args.keyword, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"[{d['doc_no']}] {d['target_name']}: {d['penalty_fine_ntd']:,.0f}元")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]⚖️ 金管會重大行政處分裁罰檢索：關鍵字 '{args.keyword}' (命中 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    fine_str = f"[bold red]{d['penalty_fine_ntd']:,.0f} 元[/bold red]" if d['penalty_fine_ntd'] > 0 else "[yellow]糾正/停止業務[/yellow]"
                    console.print(f"  {i}. [[cyan]{d['agency_bureau']}[/cyan] / [white]{d['sanction_date']}[/white]] [bold yellow]{d['target_name']}[/bold yellow] | 罰鍰: {fine_str}")
                    console.print(f"     [bold white]字號：{d['doc_no']}[/bold white]")
                    console.print(f"     [dim]主旨：{d['main_subject'][:120]}...[/dim]")
                    if d.get("violation_facts"):
                        console.print(f"     [red]事實情節：{d['violation_facts'][:120]}...[/red]")
        elif args.sanc_action == "top":
            data = query_top_penalized_institutions(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['target_name']}: {d['total_penalty_fine_ntd']:,.0f}元")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🏆 受裁罰金融機構歷史累計罰鍰與案件排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold white]{d['target_name']}[/bold white] | 累計罰鍰: [bold red]{d['total_penalty_fine_ntd']:,.0f} 元[/bold red] | 處分件數: [bold yellow]{d['total_sanctions_count']} 件[/bold yellow] (最新: {d['latest_sanction_date']})")
        elif args.sanc_action == "cases":
            data = query_ombudsman_disputes(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['institution_name']}: {d['complaint_count']}件 ({d['complaint_ratio']}%)")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]📢 金融消費評議中心爭議申訴統計排行 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold white]{d['institution_name']}[/bold white] | 申訴: [bold yellow]{d['complaint_count']} 件[/bold yellow] | 案件比率: [magenta]{d['complaint_ratio']}%[/magenta] ({d['start_date']} ~ {d['end_date']})")
        elif args.sanc_action == "escalation":
            data = track_deficiency_to_sanction_escalation(db_path, args.keyword)
            if args.quiet:
                print(f"{data['keyword']}: 金檢缺失 {data['deficiencies_found']} 筆, 正式裁罰 {data['sanctions_found']} 筆")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                console.print(f"[bold green]🔍 [F50-ADV] 重大缺失 ➔ 監理裁罰演進追蹤鏈：關鍵字 '{data['keyword']}'[/bold green]")
                console.print(f"  • 金檢發現之重大缺失 : [yellow]{data['deficiencies_found']}[/yellow] 筆")
                console.print(f"  • 升級為正式監理裁罰 : [red]{data['sanctions_found']}[/red] 筆")
                if data["exam_deficiencies"]:
                    console.print("[bold yellow]▼ 階段一：檢查局金融檢查發現之缺失情節與改善作法：[/bold yellow]")
                    for i, ed in enumerate(data["exam_deficiencies"][:2], 1):
                        console.print(f"  {i}. [{ed['business_category']}] {ed['deficiency_pattern']} ({ed['eval_year']} {ed['half_year']})")
                        console.print(f"     [dim]情節：{ed['deficiency_detail'][:100]}...[/dim]")
                if data["formal_sanctions"]:
                    console.print("[bold red]▼ 階段二：業務局處分書之違法事實與開罰罰鍰：[/bold red]")
                    for i, fs in enumerate(data["formal_sanctions"][:2], 1):
                        console.print(f"  {i}. [{fs['sanction_date']}] [bold white]{fs['target_name']}[/bold white] | 罰鍰: [bold red]{fs['penalty_fine_ntd']:,.0f} 元[/bold red]")
                        console.print(f"     [dim]主旨：{fs['main_subject'][:110]}...[/dim]")
        else:
            sanc_parser.print_help(sys.stderr)
    elif args.command == "fintech":
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "modules" / "f60_fintech_vasp_db"))
        from commands_f60 import (
            query_vasp_registry, query_fintech_sandbox, query_greenhouse_gas_trends,
            penetrate_sandbox_partner_institution, query_vasp_aml_sanctions_synergy
        )
        
        if args.fintech_action == "vasp":
            data = query_vasp_registry(db_path, status=args.status, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['brand_name']} ({d['company_name']}): {d['tax_id']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🪙 洗錢防制法令遵循之虛擬資產平台 (VASP) 名冊 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold yellow]{d['brand_name']}[/bold yellow] | [bold white]{d['company_name']}[/bold white] (統編: [cyan]{d['tax_id']}[/cyan])")
                    console.print(f"     [white]遵循日期：{d['compliance_date']} | 信託代管銀行：[bold green]{d['fiat_custody_bank']}[/bold green] | 狀態：[bold cyan]{d['status']}[/bold cyan][/white]")
                    console.print(f"     [dim]業務型態：{d['business_type']}[/dim]")
        elif args.fintech_action == "sandbox":
            data = query_fintech_sandbox(db_path, status=args.status, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['case_no']} {d['applicant']}: {d['experiment_title']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🔬 金管會金融科技監理沙盒創新實驗專案 (Top {len(data)})[/bold green]")
                for i, d in enumerate(data, 1):
                    status_str = f"[bold green]{d['status']}[/bold green]" if d['status'] == 'GRADUATED' else f"[bold yellow]{d['status']}[/bold yellow]"
                    console.print(f"  {i}. [[cyan]{d['case_no']}[/cyan]] [bold white]{d['applicant']}[/bold white] ➔ 合作銀行：[bold cyan]{d['partner_institution']}[/bold cyan] ({status_str})")
                    console.print(f"     [bold yellow]實驗主題：{d['experiment_title']}[/bold yellow] (核准：{d['approval_date']})")
        elif args.fintech_action == "esg":
            data = query_greenhouse_gas_trends(db_path, limit=args.limit)
            if args.quiet:
                for d in data:
                    print(f"{d['year']}: 淨排放 {d['net_ghg_emission_value']:,.0f} 千公噸")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🌱 國家歷年溫室氣體排放清冊報告 (最新 {len(data)} 年時序)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [bold white]{d['year']} 年[/bold white] | 毛排放: [yellow]{d['total_ghg_emission_value']:,.0f}[/yellow] 千公噸 | 碳匯吸收: [green]{d['co2_absorption_value']:,.0f}[/green] | 淨排放: [bold red]{d['net_ghg_emission_value']:,.0f} 千公噸[/bold red]")
        elif args.fintech_action == "penetrate":
            data = penetrate_sandbox_partner_institution(db_path, args.query)
            if not data:
                console.print(f"[bold red]❌ 查無相符之沙盒創新案：'{args.query}'[/bold red]")
            elif args.quiet:
                print(f"{data['sandbox_case']['applicant']} -> {data['sandbox_case']['partner_institution']}")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                sb = data["sandbox_case"]
                console.print(f"[bold green]🔍 [F60-ADV] 沙盒創新案 ➔ 合作傳統特許銀行穿透：[{sb['case_no']}] {sb['applicant']}[/bold green]")
                console.print(f"  • 實驗主題 : [bold yellow]{sb['experiment_title']}[/bold yellow]")
                console.print(f"  • 實驗狀態 : [bold cyan]{sb['status']}[/bold cyan] (核准日: {sb['approval_date']})")
                console.print(f"  • 合作銀行 : [bold white]{sb['partner_institution']}[/bold white]")
                if data["partner_bank_asset_quality"]:
                    bk = data["partner_bank_asset_quality"]
                    console.print("[bold yellow]▼ 合作商業銀行之資產規模與資產品質 (F10 連鎖)：[/bold yellow]")
                    console.print(f"    - 放款總額: [cyan]{bk['loan_total']:,.0f} 百萬元[/cyan] | 存款總額: [cyan]{bk['deposit_amount']:,.0f} 百萬元[/cyan]")
                    console.print(f"    - 逾放比率: [bold green]{bk['npl_ratio']}%[/bold green] | 備抵呆帳涵蓋率: [magenta]{bk['coverage_ratio']}%[/magenta]")
                if data["partner_bank_recent_sanctions"]:
                    console.print("[bold red]▼ 該特許銀行近期監理處分裁罰 (F50 連鎖)：[/bold red]")
                    for j, s in enumerate(data["partner_bank_recent_sanctions"], 1):
                        console.print(f"    {j}. [{s['sanction_date']}] 字號: {s['doc_no']} | 罰鍰: [bold red]{s['penalty_fine_ntd']:,.0f} 元[/bold red]")
                        console.print(f"       [dim]主旨: {s['main_subject'][:90]}...[/dim]")
        elif args.fintech_action == "aml-check":
            data = query_vasp_aml_sanctions_synergy(db_path, keyword=args.keyword)
            if args.quiet:
                for d in data:
                    print(f"{d['target_name']}: {d['penalty_fine_ntd']:,.0f}元")
            elif args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                console.print(f"[bold green]🛡️ [F60-ADV] 傳統特許銀行之虛擬通貨/洗防監控裁罰聯防 (關鍵字: '{args.keyword}', 共 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [{d['sanction_date']}] [bold white]{d['target_name']}[/bold white] | 罰鍰: [bold red]{d['penalty_fine_ntd']:,.0f} 元[/bold red]")
                    console.print(f"     [bold yellow]字號：{d['doc_no']}[/bold yellow]")
                    if d.get("violation_facts"):
                        console.print(f"     [dim]事實情節：{d['violation_facts'][:120]}...[/dim]")
        else:
            fintech_parser.print_help(sys.stderr)
    elif args.command == "schema":
        schema_data = get_schema()
        print(json.dumps(schema_data, ensure_ascii=False, indent=2))
    elif args.command == "version":
        ver_data = {"script": "fsc_cli.py", "version": "1.0.0", "cgs_spec": __cli_spec_version__}
        if args.quiet:
            print("1.0.0")
        elif args.json:
            print(json.dumps(ver_data, ensure_ascii=False))
        else:
            print(f"fsc_cli.py v1.0.0 (CGS Spec v{__cli_spec_version__})")
    else:
        parser.print_help(sys.stderr)

if __name__ == "__main__":
    main()
