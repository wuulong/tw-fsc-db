# -*- coding: utf-8 -*-
"""
[metadata]
name = "f00_handlers"
description = "tw-fsc-db CLI F00 母大腦 (全域檢索、360全景、集團關係拓樸) 之 Pipeline-Native 處理器"
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

def handle_f00_search(
    db_path: Path,
    raw_kw: Optional[str],
    limit: int,
    quiet: bool,
    json_mode: bool,
    stream_mode: bool,
    console: Console
):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f00_master_hub"))
    from commands_f00 import search_global_entities
    
    keywords = resolve_pipe_inputs(raw_kw)
    if not keywords:
        console.print("[yellow]⚠️ 請提供檢索關鍵字或透過管道傳入 (如 echo '國泰' | fsc search -j)[/yellow]")
        return
        
    all_results = []
    for kw in keywords:
        results = search_global_entities(db_path, kw, limit=limit)
        if stream_mode:
            print(json.dumps({"query": kw, "results": results}, ensure_ascii=False))
            sys.stdout.flush()
        elif quiet:
            for r in results:
                print(f"[{r['domain_code']}] {r['primary_name']}")
        elif json_mode:
            all_results.extend(results)
        else:
            console.print(f"[bold green]🔍 全域 FTS5 檢索結果：關鍵字 '{kw}' (命中 {len(results)} 筆)[/bold green]")
            for i, r in enumerate(results, 1):
                console.print(f"  {i}. [[yellow]{r['domain_code']}[/yellow]/[cyan]{r['entity_type']}[/cyan]] [bold white]{r['primary_name']}[/bold white]")
                if r.get('secondary_info'):
                    console.print(f"     [dim]{r['secondary_info'][:80]}...[/dim]")
                    
    if json_mode and not stream_mode:
        print(json.dumps(all_results, ensure_ascii=False))

def handle_f00_profile(
    db_path: Path,
    raw_kw: Optional[str],
    quiet: bool,
    json_mode: bool,
    stream_mode: bool,
    console: Console
):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f00_master_hub"))
    from commands_f00 import query_entity_360, query_entity_relations
    
    keywords = resolve_pipe_inputs(raw_kw)
    if not keywords:
        console.print("[yellow]⚠️ 請提供機構統編/名稱或透過管道傳入 (如 echo '2881' | fsc profile -j)[/yellow]")
        return
        
    all_profiles = []
    for kw in keywords:
        prof = query_entity_360(db_path, kw)
        if not prof:
            if stream_mode:
                print(json.dumps({"query": kw, "status": "NOT_FOUND"}, ensure_ascii=False))
                sys.stdout.flush()
            elif not quiet and not json_mode:
                console.print(f"[bold red]❌ 查無實體檔案：'{kw}'[/bold red]")
            continue
            
        if stream_mode:
            print(json.dumps(prof, ensure_ascii=False))
            sys.stdout.flush()
        elif quiet:
            print(f"{prof.get('canonical_name')} [{prof.get('entity_class')}]")
        elif json_mode:
            all_profiles.append(prof)
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
                console.print(f"  • 估值與殖利率 (F20)     : {pe_str} | {yield_str}")
            if prof.get("insurer_inner_staff") is not None or prof.get("insurer_actuary_count") is not None:
                i_type_zh = "人壽保險" if prof.get("insurer_type") == "LIFE" else ("產物保險" if prof.get("insurer_type") == "PROPERTY" else "保險機構")
                console.print(f"  • 保險專業人力佈局 (F30) : 類型 [{i_type_zh}] | 精算: [bold yellow]{prof.get('insurer_actuary_count', 0)}人[/bold yellow] | 核保: {prof.get('insurer_underwriting_count', 0)}人 | 理賠: {prof.get('insurer_claim_count', 0)}人")
            if prof.get("ombudsman_complaint_count") is not None:
                console.print(f"  • 消費爭議申訴統計 (F50) : 評議中心受理 [bold yellow]{prof.get('ombudsman_complaint_count', 0)} 件[/bold yellow] (申訴案件比率: [magenta]{prof.get('ombudsman_complaint_ratio')}%[/magenta])")
            if prof.get("vasp_id"):
                console.print(f"  • 虛擬資產平台合規 (F60) : 登記碼 [{prof['vasp_id']}] | 品牌: [bold yellow]{prof.get('vasp_brand_name')}[/bold yellow] | 信託銀行: [bold green]{prof.get('vasp_fiat_bank')}[/bold green]")
            if prof.get("sandbox_case_no"):
                s_status = f"[bold green]{prof['sandbox_status']}[/bold green]" if prof['sandbox_status'] == 'GRADUATED' else f"[bold yellow]{prof['sandbox_status']}[/bold yellow]"
                console.print(f"  • 金融科技監理沙盒 (F60) : 案號 [{prof['sandbox_case_no']}] | 合作銀行: [bold white]{prof.get('sandbox_partner_institution')}[/bold white] | 狀態: {s_status}")
            risk = prof.get("composite_risk_level") or "GREEN"
            def_cnt = prof.get("exam_deficiency_count") or 0
            sanc_cnt = prof.get("total_sanctions_count") or 0
            fine_ntd = prof.get("total_penalty_fine_ntd") or 0.0
            risk_color = "green" if "GREEN" in risk else ("yellow" if "YELLOW" in risk else "red")
            console.print(f"  • 綜合監理風險指標       : [{risk_color}][{risk}][/{risk_color}] (金檢缺失: [bold yellow]{def_cnt} 次[/bold yellow] | 裁罰: [bold red]{sanc_cnt} 件[/bold red] / [bold red]{fine_ntd:,.0f} 元[/bold red])")
            
            rels = query_entity_relations(db_path, kw)
            if rels.get("subsidiaries"):
                console.print(f"  • 集團控制力子公司 (F00) : 掌控 [bold yellow]{len(rels['subsidiaries'])}[/bold yellow] 家持牌或關係機構")
                for sub in rels["subsidiaries"][:3]:
                    console.print(f"    ├─ [{sub['related_class']}] [cyan]{sub['related_name']}[/cyan] ({sub['relation_type']} {sub['shareholding_ratio']}%)")
                    
    if json_mode and not stream_mode:
        if len(all_profiles) == 1 and raw_kw and raw_kw != "-":
            print(json.dumps(all_profiles[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(all_profiles, ensure_ascii=False))

def handle_f00_relations(
    db_path: Path,
    raw_kw: Optional[str],
    quiet: bool,
    json_mode: bool,
    stream_mode: bool,
    console: Console
):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f00_master_hub"))
    from commands_f00 import query_entity_relations
    
    keywords = resolve_pipe_inputs(raw_kw)
    if not keywords:
        console.print("[yellow]⚠️ 請提供金控名稱或透過管道傳入 (如 echo '富邦金' | fsc relations -j)[/yellow]")
        return
        
    all_rels = []
    for kw in keywords:
        res = query_entity_relations(db_path, kw)
        ent = res.get("entity")
        if not ent:
            if stream_mode:
                print(json.dumps({"query": kw, "status": "NOT_FOUND"}, ensure_ascii=False))
                sys.stdout.flush()
            elif not quiet and not json_mode:
                console.print(f"[bold red]❌ 查無實體或未建立關聯：'{kw}'[/bold red]")
            continue
            
        if stream_mode:
            print(json.dumps(res, ensure_ascii=False))
            sys.stdout.flush()
        elif quiet:
            print(f"{ent['canonical_name']}: 子公司 {len(res['subsidiaries'])}, 母/股東 {len(res['parents_or_shareholders'])}")
        elif json_mode:
            all_rels.append(res)
        else:
            console.print(f"[bold green]🕸️ 金管會跨模組集團股權與控制力拓樸樹：[white]{ent['canonical_name']}[/white] ({ent['entity_class']})[/bold green]")
            if res["parents_or_shareholders"]:
                console.print("[bold yellow]▲ 上游控制來源 (母公司 / 金控集團 / 逾10%大股東)：[/bold yellow]")
                for i, p in enumerate(res["parents_or_shareholders"], 1):
                    console.print(f"  {i}. [{p['related_class']}] [bold white]{p['related_name']}[/bold white] | 關係: [cyan]{p['relation_type']}[/cyan] | 控制: {p['control_level']} ({p['shareholding_ratio']}%)")
            if res["subsidiaries"]:
                console.print(f"[bold cyan]▼ 下游受控實體 (共 {len(res['subsidiaries'])} 家)：[/bold cyan]")
                for i, s in enumerate(res["subsidiaries"][:5], 1):
                    console.print(f"  {i}. [{s['related_class']}] [bold white]{s['related_name']}[/bold white] | 持股: [green]{s['shareholding_ratio']}%[/green]")
                    
    if json_mode and not stream_mode:
        if len(all_rels) == 1 and raw_kw and raw_kw != "-":
            print(json.dumps(all_rels[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(all_rels, ensure_ascii=False))
