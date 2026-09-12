# -*- coding: utf-8 -*-
"""
[metadata]
name = "f20_handlers"
description = "tw-fsc-db CLI F20 證券市場 (公司營收、檔案、大股東、估值、期貨) 之 Pipeline-Native 處理器"
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

def handle_f20_company(
    db_path: Path,
    action: Optional[str],
    args: Any,
    quiet: bool,
    json_mode: bool,
    stream_mode: bool,
    console: Console
):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f20_securities_markets_db"))
    from commands_f20 import (
        query_top_revenue_companies,
        query_company_profile,
        query_major_shareholders,
        query_market_valuations,
        query_futures_trading
    )
    
    if action == "top":
        data = query_top_revenue_companies(db_path, limit=args.limit, min_yoy=args.min_yoy)
        if quiet:
            for d in data:
                print(f"{d['company_code']} {d['company_name']}: {d['current_month_revenue']}千元")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            title = "📈 上市公司營收排行" if args.min_yoy is None else f"🚀 上市公司營收高成長排行 (YoY >= {args.min_yoy}%)"
            console.print(f"[bold green]{title} (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [{d['company_code']}] [bold cyan]{d['company_name']}[/bold cyan] ({d.get('industry_name', '未分類')}) | 當月營收: [yellow]{d['current_month_revenue']:,.0f} 千元[/yellow] | YoY: [green]{d['yoy_growth_rate']}%[/green]")
                
    elif action == "profile":
        raw_q = getattr(args, "query", None)
        queries = resolve_pipe_inputs(raw_q)
        if not queries:
            console.print("[yellow]⚠️ 請提供股票程式碼/公司名稱或透過管道傳入 (如 echo '2881' | fsc company profile -j)[/yellow]")
            return
            
        all_profiles = []
        for q in queries:
            prof = query_company_profile(db_path, q)
            if not prof:
                if stream_mode:
                    print(json.dumps({"query": q, "status": "NOT_FOUND"}, ensure_ascii=False))
                    sys.stdout.flush()
                elif not quiet and not json_mode:
                    console.print(f"[yellow]⚠️ 找不到與 '{q}' 相符的公司 profile。[/yellow]")
                continue
                
            if stream_mode:
                print(json.dumps(prof, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                print(f"{prof['company_code']} {prof['company_name']}")
            elif json_mode:
                all_profiles.append(prof)
            else:
                console.print(f"[bold green]🏢 公司全維度營收與股權 Profile：[{prof['company_code']}] {prof['company_name']}[/bold green]")
                console.print(f"  • 市場別 / 產業別 : [white]{prof['market_type']} / {prof['industry_category']}[/white]")
                console.print(f"  • 掛牌上市日期     : [cyan]{prof['listing_date']}[/cyan]")
                if prof.get("revenue_year_month"):
                    console.print(f"  • 最新月營收 ({prof['revenue_year_month']}) : [yellow]{prof['current_month_revenue']:,.0f} 千元[/yellow] (YoY: [green]{prof['yoy_growth_rate']}%[/green])")
                if prof.get("major_shareholders_count"):
                    console.print(f"  • 10% 大股東人數   : [bold]{prof['major_shareholders_count']} 位[/bold]")
                    
        if json_mode and not stream_mode:
            if len(all_profiles) == 1 and raw_q and raw_q != "-":
                print(json.dumps(all_profiles[0], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(all_profiles, ensure_ascii=False))
                
    elif action == "shareholders":
        raw_q = getattr(args, "query", None)
        queries = resolve_pipe_inputs(raw_q)
        if not queries:
            console.print("[yellow]⚠️ 請提供股票程式碼/公司名稱或透過管道傳入 (如 echo '2881' | fsc company shareholders -j)[/yellow]")
            return
            
        all_results = []
        for q in queries:
            data = query_major_shareholders(db_path, q)
            if stream_mode:
                print(json.dumps({"query": q, "shareholders": data}, ensure_ascii=False))
                sys.stdout.flush()
            elif quiet:
                for d in data:
                    print(d["shareholder_name"])
            elif json_mode:
                all_results.extend(data)
            else:
                console.print(f"[bold green]👥 公司持股逾 10% 大股東名單：'{q}' (共 {len(data)} 位)[/bold green]")
                for i, d in enumerate(data, 1):
                    kind = "[法人機構]" if d.get("is_corporate") == 1 else "[自然人]"
                    console.print(f"  {i}. [cyan]{kind}[/cyan] [bold white]{d['shareholder_name']}[/bold white] (基準日: {d['report_date']})")
                    
        if json_mode and not stream_mode:
            print(json.dumps(all_results, ensure_ascii=False))
            
    elif action == "valuation":
        data = query_market_valuations(db_path, limit=args.limit, min_yield=args.min_yield, max_pe=args.max_pe)
        if quiet:
            for d in data:
                print(f"{d['company_code']} {d['company_name']}: {d['dividend_yield']}%")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            title = "💎 上櫃股票市場估值與高殖利率排行" if args.min_yield is None else f"💎 高殖利率精選 (殖利率 >= {args.min_yield}%)"
            console.print(f"[bold green]{title} (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [{d['company_code']}] [bold cyan]{d['company_name']}[/bold cyan] | 殖利率: [green]{d['dividend_yield']}%[/green] | P/E: [yellow]{d['pe_ratio']}[/yellow] | P/B: {d['pb_ratio']}")
                
    elif action == "futures":
        data = query_futures_trading(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['contract_code']} {d['contract_name']}: {d['total_volume']}口")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]📊 臺灣期交所主力商品交易量排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [{d['contract_code']}] [bold cyan]{d['contract_name']}[/bold cyan] ({d['trade_month']}) | 月成交量: [yellow]{d['total_volume']:,} 口[/yellow]")
