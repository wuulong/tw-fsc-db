#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: fsc_cli.py
title: 金融監督管理委員會 (tw-fsc-db / GOV-A21) 官方 CLI 工具
description: 符合 CLI Governance Spec v2.4 (Pipeline-Native) 規範之金管會開放資料庫命令列工具，支援全子命令 sys.stdin 串流管道、母大腦連鎖狀態查詢、Schema 地圖與資料庫維運。
category: cli
spec: events-2026Q3/fsc-db-in/sys_eng/02_specification/spec_cgs_v24_pipeline.md
manual: events-2026Q3/fsc-db-in/tw-fsc-db/book/07_03_appendix_cli_reference.md
dependencies: rich
cgs_version: 2.4
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

# 顯式宣告 CGS 規格版號
__cli_spec_version__ = "2.4"

# 確保可解析 src 底下模組
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 引入核心設施
from a00_core.fsc_core import get_fsc_db_path, __cli_spec_version__
from cli.handlers.status_handler import get_status, get_schema, render_status
from cli.handlers.f00_handlers import handle_f00_search, handle_f00_profile, handle_f00_relations
from cli.handlers.f10_handlers import handle_f10_bank
from cli.handlers.f20_handlers import handle_f20_company
from cli.handlers.other_handlers import (
    handle_f30_insurer,
    handle_f40_exam,
    handle_f50_sanction,
    handle_f60_fintech
)

# CGS v2.4 規範：Rich 與 UI 提示徹底隔離至 stderr
console = Console(stderr=True)

def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-j", "--json", action="store_true", help="以 JSON 格式輸出")
    common_parser.add_argument("-q", "--quiet", action="store_true", help="極簡模式輸出")
    common_parser.add_argument("-v", "--verbose", action="store_true", help="輸出詳細 Log")
    common_parser.add_argument("--stream", action="store_true", help="啟用 NDJSON 串流輸出模式")
    common_parser.add_argument("-d", "--db", type=str, default=None, help="指定 SQLite 資料庫路徑 (優先於環境變數 FSC_DB_PATH 與外接硬碟)")

    parser = argparse.ArgumentParser(
        description="金融監督管理委員會 (tw-fsc-db / GOV-A21) 官方 CLI 指令列工具 (Pipeline-Native)",
        parents=[common_parser]
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # F00 全域檢索子命令 (支援 pipe)
    search_p = subparsers.add_parser("search", parents=[common_parser], help="全域 FTS5 倒排索引關鍵字檢索 (跨金控、銀行、公發公司、裁罰)")
    search_p.add_argument("keyword", nargs="?", default=None, help="檢索關鍵字 (可透過 pipe 輸入)")
    search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    # F00 360 度跨模組全景實體檔案子命令 (支援 pipe)
    prof_global_p = subparsers.add_parser("profile", parents=[common_parser], help="調閱機構之 360 度跨模組全景監理檔案 (統編/代號/名稱)")
    prof_global_p.add_argument("keyword", nargs="?", default=None, help="機構全銜、股票代號或統編 (可透過 pipe 輸入)")

    # F00 跨模組集團控制力與股權網路拓樸子命令 (支援 pipe)
    rel_p = subparsers.add_parser("relations", parents=[common_parser], help="查詢金融控股集團股權控制鏈與大股東持股網路")
    rel_p.add_argument("keyword", nargs="?", default=None, help="金控名稱、銀行全銜、上市公司代號 (可透過 pipe 輸入)")

    # F20 證券與公開發行公司子命令
    comp_p = subparsers.add_parser("company", parents=[common_parser], help="查詢公開發行公司、營收排行與大股東名冊")
    comp_sub = comp_p.add_subparsers(dest="comp_action", help="證券模組操作")
    
    top_rev_p = comp_sub.add_parser("top", parents=[common_parser], help="查詢當月營收或年增率最高公司")
    top_rev_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    top_rev_p.add_argument("--min-yoy", type=float, default=None, help="最低 YoY 年增率門檻 (%)")
    
    prof_p = comp_sub.add_parser("profile", parents=[common_parser], help="一鍵查詢公司基本面、最新月營收與大股東名冊")
    prof_p.add_argument("query", nargs="?", default=None, help="公司代號或名稱 (可透過 pipe 輸入)")
    
    sh_p = comp_sub.add_parser("shareholders", parents=[common_parser], help="查詢特定公司持股逾 10% 大股東名冊")
    sh_p.add_argument("query", nargs="?", default=None, help="公司代號或名稱 (可透過 pipe 輸入)")

    val_p = comp_sub.add_parser("valuation", parents=[common_parser], help="查詢上櫃股票本益比、殖利率與股價淨值比排行")
    val_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    val_p.add_argument("--min-yield", type=float, default=None, help="最低殖利率門檻 (%)")
    val_p.add_argument("--max-pe", type=float, default=None, help="最高本益比門檻")

    fut_p = comp_sub.add_parser("futures", parents=[common_parser], help="查詢期交所主力期貨商品月成交量與未平倉排行")
    fut_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

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

    # F40 金融檢查重大缺失子命令
    exam_parser = subparsers.add_parser("exam", parents=[common_parser], help="查詢檢查局金融檢查重大缺失、FTS5違規檢索與年度執行統計")
    exam_sub = exam_parser.add_subparsers(dest="exam_action", help="金融檢查模組操作")
    
    exam_search_p = exam_sub.add_parser("search", parents=[common_parser], help="透過 FTS5 全文檢索金融檢查重大缺失態樣與情節")
    exam_search_p.add_argument("keyword", nargs="?", default=None, help="檢索關鍵字 (可透過 pipe 輸入)")
    exam_search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")
    exam_search_p.add_argument("--sector", choices=["HOLDING", "FOREIGN_BANK"], default=None, help="篩選受檢業別")

    exam_cat_p = exam_sub.add_parser("categories", parents=[common_parser], help="查詢重大缺失高頻業務專案分佈統計")
    exam_cat_p.add_argument("--sector", choices=["HOLDING", "FOREIGN_BANK"], default=None, help="篩選受檢業別")

    exam_exec_p = exam_sub.add_parser("execution", parents=[common_parser], help="查詢檢查局實地檢查受檢機構年度執行統計")
    exam_exec_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")
    exam_exec_p.add_argument("--year", default=None, help="篩選統計年度")

    exam_pen_p = exam_sub.add_parser("penetrate", parents=[common_parser], help="[進階] 缺失態樣穿透集團股權拓樸 (關聯受檢金控之子公司管理缺失與轄下受控實體)")
    exam_pen_p.add_argument("holding", nargs="?", default=None, help="金控名稱或代號 (可透過 pipe 輸入)")

    # F50 法律事務、處分裁罰與評議爭議子命令
    sanc_parser = subparsers.add_parser("sanction", parents=[common_parser], help="查詢金管會重大裁處處分書、FTS5違法事實檢索與金融消費爭議")
    sanc_sub = sanc_parser.add_subparsers(dest="sanc_action", help="裁罰與法律模組操作")
    
    sanc_search_p = sanc_sub.add_parser("search", parents=[common_parser], help="透過 FTS5 全文倒排檢索正式裁罰處分書 (案號、事實、法條)")
    sanc_search_p.add_argument("keyword", nargs="?", default=None, help="檢索關鍵字 (可透過 pipe 輸入)")
    sanc_search_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    sanc_top_p = sanc_sub.add_parser("top", parents=[common_parser], help="查詢受裁罰金融機構歷史累計罰鍰與處分件數排行")
    sanc_top_p.add_argument("-n", "--limit", type=int, default=5, help="限制輸出筆數")

    sanc_case_p = sanc_sub.add_parser("cases", parents=[common_parser], help="查詢金融消費評議中心銀行業爭議申訴統計排行")
    sanc_case_p.add_argument("-n", "--limit", type=int, default=10, help="限制輸出筆數")

    sanc_esc_p = sanc_sub.add_parser("escalation", parents=[common_parser], help="[進階] 重大缺失 ➔ 監理裁罰演進追蹤 (F40 檢查缺失比對 F50 正式裁處)")
    sanc_esc_p.add_argument("keyword", nargs="?", default=None, help="業務或違規關鍵字 (可透過 pipe 輸入)")

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
    fin_pen_p.add_argument("query", nargs="?", default=None, help="沙盒案號或申請機構 (可透過 pipe 輸入)")

    vasp_aml_p = fintech_sub.add_parser("aml-check", parents=[common_parser], help="[進階] 傳統銀行之虛擬通貨 (VASP) 監控缺失裁罰聯防")
    vasp_aml_p.add_argument("keyword", nargs="?", default="虛擬", help="檢索關鍵字 (可透過 pipe 輸入)")

    subparsers.add_parser("status", parents=[common_parser], help="顯示本部會資料庫運作狀態與母大腦連鎖狀態")
    subparsers.add_parser("schema", parents=[common_parser], help="輸出 JSON Schema 與命令地圖")
    subparsers.add_parser("version", parents=[common_parser], help="顯示 CLI 版本資訊")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    args = parser.parse_args()
    db_path, _ = get_fsc_db_path(getattr(args, "db", None))
    q_mode = getattr(args, "quiet", False)
    j_mode = getattr(args, "json", False)
    s_mode = getattr(args, "stream", False)

    if args.command == "status":
        status_data = get_status(getattr(args, "db", None))
        render_status(status_data, console, quiet=q_mode, json_mode=j_mode)
    elif args.command == "search":
        handle_f00_search(db_path, args.keyword, args.limit, q_mode, j_mode, s_mode, console)
    elif args.command == "profile":
        handle_f00_profile(db_path, args.keyword, q_mode, j_mode, s_mode, console)
    elif args.command == "relations":
        handle_f00_relations(db_path, args.keyword, q_mode, j_mode, s_mode, console)
    elif args.command == "company":
        handle_f20_company(db_path, args.comp_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "bank":
        handle_f10_bank(db_path, args.bank_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "insurer":
        handle_f30_insurer(db_path, args.ins_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "exam":
        handle_f40_exam(db_path, args.exam_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "sanction":
        handle_f50_sanction(db_path, args.sanc_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "fintech":
        handle_f60_fintech(db_path, args.fintech_action, args, q_mode, j_mode, s_mode, console)
    elif args.command == "schema":
        print(json.dumps(get_schema(), ensure_ascii=False, indent=2))
    elif args.command == "version":
        ver_data = {"script": "fsc_cli.py", "version": "1.2.0", "cgs_spec": __cli_spec_version__}
        if q_mode:
            print("1.2.0")
        elif j_mode:
            print(json.dumps(ver_data, ensure_ascii=False))
        else:
            print(f"fsc_cli.py v1.2.0 (CGS Spec v{__cli_spec_version__})")
    else:
        parser.print_help(sys.stderr)

if __name__ == "__main__":
    main()
