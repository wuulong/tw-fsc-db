# -*- coding: utf-8 -*-
"""
[metadata]
name = "f10_handlers"
description = "tw-fsc-db CLI F10 銀行與金控信用業務之 Pipeline-Native 處理器"
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

def handle_f10_bank(
    db_path: Path,
    action: Optional[str],
    args: Any,
    quiet: bool,
    json_mode: bool,
    stream_mode: bool,
    console: Console
):
    from a00_core.fsc_core import resolve_pipe_inputs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules" / "f10_banking_credit_db"))
    from commands_f10 import (
        query_financial_holdings,
        query_bank_asset_quality,
        query_land_collateral_loans,
        query_credit_card_operations,
        query_corporate_loan_trends,
        query_bank_credit_risk_radar
    )
    
    if action == "holdings":
        data = query_financial_holdings(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(d["holding_name"])
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🏛️ 全臺主要金融控股公司資產排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold cyan]{d['holding_name']}[/bold cyan] | 集團資產: [yellow]{d['group_assets_billion']:,.0f} 億元[/yellow] | 子公司: {d['subsidiaries_count']} 家")
                
    elif action == "quality":
        data = query_bank_asset_quality(db_path, limit=args.limit, max_npl=args.max_npl)
        if quiet:
            for d in data:
                print(f"{d['bank_name']}: {d['npl_ratio']}%")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]📊 本國銀行資產品質排行 (放款規模 Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 放款: [white]{d['loan_total']:,.0f} 百萬元[/white] | 逾放比: [green]{d['npl_ratio']}%[/green] | 涵蓋率: {d['coverage_ratio']:,.1f}%")
                
    elif action == "land":
        data = query_land_collateral_loans(db_path, limit=args.limit, min_ratio=args.min_ratio)
        if quiet:
            for d in data:
                print(f"{d['bank_name']}: {d['land_loan_balance']}百萬")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🏞️ 銀行土地擔保放款與集中度排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 土地融資: [yellow]{d['land_loan_balance']:,.0f} 百萬元[/yellow] | 佔比: [magenta]{d['land_loan_ratio']}%[/magenta]")
                
    elif action == "cards":
        data = query_credit_card_operations(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['institution_name']}: {d['signing_amount_million']}百萬")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]💳 信用卡業務與簽帳消費力排行 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  {i}. [bold cyan]{d['institution_name']}[/bold cyan] | 簽帳金額: [yellow]{d['signing_amount_million']:,.1f} 百萬元[/yellow] | 活卡率: [green]{d['active_card_ratio']}%[/green]")
                
    elif action == "corporate":
        data = query_corporate_loan_trends(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['year_month']}: {d['loan_total_billion']}十億")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🏭 聯徵中心全台企業總貸款趨勢 (近 {len(data)} 個月)[/bold green]")
            for i, d in enumerate(data, 1):
                console.print(f"  • [cyan]{d['year_month']}[/cyan] | 貸款總額: [yellow]{d['loan_total_billion']:,.2f} 億元[/yellow]")
                
    elif action == "radar":
        data = query_bank_credit_risk_radar(db_path, limit=args.limit)
        if quiet:
            for d in data:
                print(f"{d['bank_name']}: {d['supervisory_risk_badge']}")
        elif json_mode:
            print(json.dumps(data, ensure_ascii=False))
        else:
            console.print(f"[bold green]🛡️ 商業銀行信用風險監理綜合雷達 (Top {len(data)})[/bold green]")
            for i, d in enumerate(data, 1):
                badge = d['supervisory_risk_badge']
                color = "green" if badge == "GREEN" else ("yellow" if badge == "YELLOW" else "red")
                console.print(f"  {i}. [bold cyan]{d['bank_name']}[/bold cyan] | 放款: {d['loan_total']:,.0f}M | 逾放: {d['npl_ratio']}% | 燈號: [{color}][{badge}][/{color}]")
