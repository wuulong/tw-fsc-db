# -*- coding: utf-8 -*-
"""
[metadata]
name = "other_handlers"
description = "tw-fsc-db CLI F30, F40, F50, F60 模組之 Pipeline-Native 處理器"
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

def handle_f30_insurer(db_path: Path, action: Optional[str], args: Any, quiet: bool, json_mode: bool, stream_mode: bool, console: Console):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f30_insurance_actuarial_db"))
    from commands_f30 import query_insurance_institutions, query_complaint_trends, query_compensation_fund
    
    if action == "list":
        data = query_insurance_institutions(db_path, limit=args.limit, institution_type=args.type, order_by=args.sort)
        if quiet:
            for d in data:
                print(f"{d['insurer_name']}: 精算 {d['actuary_count']}人")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🛡️ 保險機構人力與精算專業配置排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                t_zh = "人壽" if d['insurer_type'] == "LIFE" else "產險"
                console.print(f"  {i}. [bold cyan]{d['insurer_name']}[/bold cyan] ({t_zh}) | 精算: [bold yellow]{d['actuary_count']}人[/bold yellow] | 核保: {d['underwriting_count']}人 | 外勤: {d['field_agent_count']:,}人")
    elif action == "complaints":
        data = query_complaint_trends(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['eval_year']}: 申訴 {d['complaint_count']}件")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]⚖️ 全台保險消費爭議申訴與和解趨勢 (近 {len(data)} 年)[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  • [cyan]{d['eval_year']} 年[/cyan] | 申訴: [yellow]{d['complaint_count']:,} 件[/yellow] | 申訴率: {d['complaint_ratio']}% | 和解率: [green]{d['settlement_ratio']}%[/green]")
    elif action == "fund":
        data = query_compensation_fund(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['stat_year']}: 平均 {d['avg_compensation_thousand']}仟元")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🚗 汽車交通事故特別補償基金運作趨勢 (近 {len(data)} 年)[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  • [cyan]{d['stat_year']} 年[/cyan] | 支出: [yellow]{d['compensation_expense_thousand']:,.0f} 仟元[/yellow] | 平均給付: [bold green]{d['avg_compensation_thousand']:,.1f} 仟元[/bold green]")

def handle_f40_exam(db_path: Path, action: Optional[str], args: Any, quiet: bool, json_mode: bool, stream_mode: bool, console: Console):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f40_inspection_bureau_db"))
    from commands_f40 import search_exam_deficiencies, query_deficiency_categories, query_inspection_executions, query_holding_deficiency_penetration
    
    if action == "search":
        raw_kw = getattr(args, "keyword", None)
        kws = resolve_pipe_inputs(raw_kw)
        if not kws:
            console.print("[yellow]⚠️ 請提供檢索關鍵字或透過管道傳入 (如 echo '不動產' | fsc exam search -j)[/yellow]")
            return
            
        all_data = []
        for kw in kws:
            data = search_exam_deficiencies(db_path, kw, target_sector=args.sector, limit=args.limit)
            if stream_mode:
                print(json.dumps({"keyword": kw, "results": data}, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                for d in data:
                    print(f"[{d['target_sector']}] {d['deficiency_pattern']}")
            elif json_mode:
                all_data.extend(data)
            else:
                console.print(f"[bold green]🔍 檢查局重大缺失檢索：關鍵字 '{kw}' (命中 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    sec_zh = "金控公司" if d['target_sector'] == "HOLDING" else "外銀在臺分行"
                    console.print(f"  {i}. [[yellow]{sec_zh}[/yellow] / [cyan]{d['business_category']}[/cyan]] [bold white]{d['deficiency_pattern']}[/bold white] ({d['eval_year']} {d['half_year']})")
                    console.print(f"     [dim]情節：{d['deficiency_detail'][:100]}...[/dim]")
        if json_mode and not stream_mode:
            print(json.dumps(all_data, ensure_ascii=False))
            
    elif action == "categories":
        data = query_deficiency_categories(db_path, target_sector=args.sector)
        if quiet:
            for d in data:
                print(f"{d['business_category']}: {d['deficiency_count']}")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print("[bold green]📊 重大內控與法遵缺失業務專案統計排行[/bold green]")
            for i, d in enumerate(data, 1):
                sec_zh = "金控公司" if d['target_sector'] == "HOLDING" else "外銀在臺分行"
                console.print(f"  {i}. [{sec_zh}] [bold cyan]{d['business_category']}[/bold cyan] : [bold yellow]{d['deficiency_count']} 件[/bold yellow] (佔比 {d['category_pct']}%)")
                
    elif action == "execution":
        data = query_inspection_executions(db_path, eval_year=args.year, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['eval_year']} {d['target_sector']}: {d['inspected_count']}家")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🏛️ 檢查局實地檢查受檢機構執行家數統計 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [cyan]{d['eval_year']} 年[/cyan] | [yellow]{d['target_sector']}[/yellow] : [bold green]{d['inspected_count']:,} 家[/bold green]")
                
    elif action == "penetrate":
        raw_h = getattr(args, "holding", None)
        holdings = resolve_pipe_inputs(raw_h)
        if not holdings:
            console.print("[yellow]⚠️ 請提供金控名稱或透過管道傳入 (如 echo '富邦金' | fsc exam penetrate -j)[/yellow]")
            return
            
        all_pens = []
        for h in holdings:
            data = query_holding_deficiency_penetration(db_path, h)
            if stream_mode:
                print(json.dumps(data, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                print(f"{data['holding_name']}: 子公司 {data['subsidiaries_count']} 家, 缺失 {data['deficiencies_count']} 筆")
            elif json_mode:
                all_pens.append(data)
            else:
                console.print(f"[bold green]🕸️ [F40-ADV] 金檢缺失穿透集團股權拓樸：[white]{data['holding_name']}[/white][/bold green]")
                console.print(f"  • 關聯受控子公司家數 : [bold yellow]{data['subsidiaries_count']}[/bold yellow] 家")
                console.print(f"  • 督導子公司相關缺失 : [bold red]{data['deficiencies_count']}[/bold red] 筆")
        if json_mode and not stream_mode:
            if len(all_pens) == 1 and raw_h and raw_h != "-":
                print(json.dumps(all_pens[0], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(all_pens, ensure_ascii=False))

def handle_f50_sanction(db_path: Path, action: Optional[str], args: Any, quiet: bool, json_mode: bool, stream_mode: bool, console: Console):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f50_sanctions_legal_db"))
    from commands_f50 import search_sanctions, query_top_penalized_institutions, query_ombudsman_disputes, track_deficiency_to_sanction_escalation
    
    if action == "search":
        raw_kw = getattr(args, "keyword", None)
        kws = resolve_pipe_inputs(raw_kw)
        if not kws:
            console.print("[yellow]⚠️ 請提供檢索關鍵字或透過管道傳入 (如 echo '洗錢' | fsc sanction search -j)[/yellow]")
            return
            
        all_data = []
        for kw in kws:
            data = search_sanctions(db_path, kw, limit=args.limit)
            if stream_mode:
                print(json.dumps({"keyword": kw, "results": data}, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                for d in data:
                    print(f"[{d['doc_no']}] {d['target_name']}: {d['penalty_fine_ntd']:,.0f}元")
            elif json_mode:
                all_data.extend(data)
            else:
                console.print(f"[bold green]⚖️ 金管會重大行政處分裁罰檢索：關鍵字 '{kw}' (命中 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    fine_str = f"[bold red]{d['penalty_fine_ntd']:,.0f} 元[/bold red]" if d['penalty_fine_ntd'] > 0 else "[yellow]糾正/停止業務[/yellow]"
                    console.print(f"  {i}. [[cyan]{d['agency_bureau']}[/cyan] / [white]{d['sanction_date']}[/white]] [bold yellow]{d['target_name']}[/bold yellow] | 罰鍰: {fine_str}")
                    console.print(f"     [bold white]字號：{d['doc_no']}[/bold white]")
                    console.print(f"     [dim]主旨：{d['main_subject'][:100]}...[/dim]")
        if json_mode and not stream_mode:
            print(json.dumps(all_data, ensure_ascii=False))
            
    elif action == "top":
        data = query_top_penalized_institutions(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['target_name']}: {d['total_penalty_fine_ntd']:,.0f}元")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🏆 受裁罰金融機構歷史累計罰鍰與案件排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold white]{d['target_name']}[/bold white] | 累計罰鍰: [bold red]{d['total_penalty_fine_ntd']:,.0f} 元[/bold red] | 處分: {d['total_sanctions_count']} 件")
                
    elif action == "cases":
        data = query_ombudsman_disputes(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['institution_name']}: {d['complaint_count']}件 ({d['complaint_ratio']}%)")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]📢 金融消費評議中心爭議申訴統計排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold white]{d['institution_name']}[/bold white] | 申訴: [bold yellow]{d['complaint_count']} 件[/bold yellow] | 案件比率: [magenta]{d['complaint_ratio']}%[/magenta]")
                
    elif action == "escalation":
        raw_kw = getattr(args, "keyword", None)
        kws = resolve_pipe_inputs(raw_kw)
        if not kws:
            console.print("[yellow]⚠️ 請提供違規關鍵字或透過管道傳入 (如 echo '防制洗錢' | fsc sanction escalation -j)[/yellow]")
            return
        all_escs = []
        for kw in kws:
            data = track_deficiency_to_sanction_escalation(db_path, kw)
            if stream_mode:
                print(json.dumps(data, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                print(f"{data['keyword']}: 金檢缺失 {data['deficiencies_found']} 筆, 正式裁罰 {data['sanctions_found']} 筆")
            elif json_mode:
                all_escs.append(data)
            else:
                console.print(f"[bold green]🔍 [F50-ADV] 重大缺失 ➔ 監理裁罰演進追蹤鏈：關鍵字 '{data['keyword']}'[/bold green]")
                console.print(f"  • 金檢發現缺失: [yellow]{data['deficiencies_found']}[/yellow] 筆 | 正式裁罰: [red]{data['sanctions_found']}[/red] 筆")
        if json_mode and not stream_mode:
            if len(all_escs) == 1 and raw_kw and raw_kw != "-":
                print(json.dumps(all_escs[0], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(all_escs, ensure_ascii=False))

def handle_f60_fintech(db_path: Path, action: Optional[str], args: Any, quiet: bool, json_mode: bool, stream_mode: bool, console: Console):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f60_fintech_vasp_db"))
    from commands_f60 import (
        query_vasp_registry, query_fintech_sandbox, query_greenhouse_gas_trends,
        penetrate_sandbox_partner_institution, query_vasp_aml_sanctions_synergy
    )
    
    if action == "vasp":
        data = query_vasp_registry(db_path, status=args.status, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['brand_name']} ({d['company_name']}): {d['tax_id']}")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🪙 洗錢防制法令遵循之虛擬資產平台 (VASP) 名冊 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold yellow]{d['brand_name']}[/bold yellow] | [bold white]{d['company_name']}[/bold white] (統編: [cyan]{d['tax_id']}[/cyan])")
                console.print(f"     [white]遵循日期：{d['compliance_date']} | 信託代管銀行：[bold green]{d['fiat_custody_bank']}[/bold green][/white]")
                
    elif action == "sandbox":
        data = query_fintech_sandbox(db_path, status=args.status, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['case_no']} {d['applicant']}: {d['experiment_title']}")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🔬 金管會金融科技監理沙盒創新實驗專案 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [[cyan]{d['case_no']}[/cyan]] [bold white]{d['applicant']}[/bold white] ➔ 合作銀行：[bold cyan]{d['partner_institution']}[/bold cyan]")
                
    elif action == "esg":
        data = query_greenhouse_gas_trends(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['year']}: 淨排放 {d['net_ghg_emission_value']:,.0f} 千公噸")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🌱 國家歷年溫室氣體排放清冊報告 (最新 {len(data)} 年時序)[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold white]{d['year']} 年[/bold white] | 淨排放: [bold red]{d['net_ghg_emission_value']:,.0f} 千公噸[/bold red]")
                
    elif action == "penetrate":
        raw_q = getattr(args, "query", None)
        queries = resolve_pipe_inputs(raw_q)
        if not queries:
            console.print("[yellow]⚠️ 請提供沙盒案號/申請公司或透過管道傳入 (如 echo '好好投資' | fsc fintech penetrate -j)[/yellow]")
            return
        all_pens = []
        for q in queries:
            data = penetrate_sandbox_partner_institution(db_path, q)
            if not data:
                continue
            if stream_mode:
                print(json.dumps(data, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                print(f"{data['sandbox_case']['applicant']} -> {data['sandbox_case']['partner_institution']}")
            elif json_mode:
                all_pens.append(data)
            else:
                sb = data["sandbox_case"]
                console.print(f"[bold green]🔍 [F60-ADV] 沙盒 ➔ 傳統銀行穿透：[{sb['case_no']}] {sb['applicant']}[/bold green]")
                console.print(f"  • 合作銀行: [bold white]{sb['partner_institution']}[/bold white]")
        if json_mode and not stream_mode:
            if len(all_pens) == 1 and raw_q and raw_q != "-":
                print(json.dumps(all_pens[0], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(all_pens, ensure_ascii=False))
                
    elif action == "aml-check":
        raw_kw = getattr(args, "keyword", None)
        kws = resolve_pipe_inputs(raw_kw)
        if not kws:
            kws = ["虛擬"]
        all_aml = []
        for kw in kws:
            data = query_vasp_aml_sanctions_synergy(db_path, keyword=kw)
            if stream_mode:
                print(json.dumps({"keyword": kw, "results": data}, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                for d in data:
                    print(f"{d['target_name']}: {d['penalty_fine_ntd']:,.0f}元")
            elif json_mode:
                all_aml.extend(data)
            else:
                console.print(f"[bold green]🛡️ [F60-ADV] 傳統銀行虛擬通貨洗防裁罰聯防 (關鍵字: '{kw}', 共 {len(data)} 筆)[/bold green]")
                for i, d in enumerate(data, 1):
                    console.print(f"  {i}. [{d['sanction_date']}] [bold white]{d['target_name']}[/bold white] | 罰鍰: [bold red]{d['penalty_fine_ntd']:,.0f} 元[/bold red]")
        if json_mode and not stream_mode:
            print(json.dumps(all_aml, ensure_ascii=False))
