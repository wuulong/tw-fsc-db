# -*- coding: utf-8 -*-
"""
[metadata]
name = "fsc-core"
description = "金融監督管理委員會 核心資料庫介面與適配器 (100% 引用 GOV-300 通用 Library)"
spec = "events-2026Q3/gov-db-in/sys_eng/02_specification/spec_functional.md"
manual = "README.md"
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# CGS v2.1 版號宣告
__cli_spec_version__ = "2.1"

# 預設外接磁碟資料庫路徑
EXTERNAL_FSC_DB_PATH = Path("/Volumes/D2024/data/fsc-db-in/tw-fsc-db/db/fsc.db")

def get_fsc_db_path(custom_path: Optional[str] = None) -> Tuple[Path, str]:
    """
    動態解析金管會主資料庫路徑 (四階解析順序):
    1. 命令列顯式傳入 custom_path (--db)
    2. 環境變數 FSC_DB_PATH
    3. 外部擴充磁碟預設路徑 (/Volumes/D2024/data/fsc-db-in/tw-fsc-db/db/fsc.db)
    4. 本地專案相對路徑 fallback (events-2026Q3/fsc-db-in/tw-fsc-db/db/fsc.db)

    回傳: (Path 物件, 來源說明字串)
    """
    # 1. 顯式參數
    if custom_path:
        p = Path(custom_path)
        return p, "CLI --db 參數指定"

    # 2. 環境變數 FSC_DB_PATH
    env_path = os.environ.get("FSC_DB_PATH")
    if env_path:
        p = Path(env_path)
        return p, f"環境變數 FSC_DB_PATH ({env_path})"

    # 3. 外部擴充磁碟預設路徑
    if EXTERNAL_FSC_DB_PATH.exists():
        return EXTERNAL_FSC_DB_PATH, f"外接儲存裝置預設 ({EXTERNAL_FSC_DB_PATH})"

    # 4. 本地專案相對路徑
    base_dir = Path(__file__).resolve().parent.parent.parent
    local_p = base_dir / "db" / "fsc.db"
    return local_p, f"本地專案路徑 ({local_p})"

def get_mother_gov_resolver():
    """動態取得 GOV-300 母專案導航解析器"""
    current = Path(__file__).resolve()
    gov_src = None
    for parent in [current] + list(current.parents):
        candidate = parent / "events-2026Q3" / "gov-db-in" / "tw-gov-db" / "src"
        if candidate.exists():
            gov_src = candidate
            break
        candidate2 = parent / "tw-gov-db" / "src"
        if candidate2.exists():
            gov_src = candidate2
            break

    if not gov_src:
        gov_src = Path("/Users/wuulong/github/bmad-pa/events-2026Q3/gov-db-in/tw-gov-db/src")

    if str(gov_src) not in sys.path:
        sys.path.insert(0, str(gov_src))
        
    from core.domain_registry_resolver import DomainRegistryResolver
    return DomainRegistryResolver()

def query_agency_base_info(agency_oid: str = "2.16.886.101.20003.20022") -> Dict[str, Any]:
    """呼叫 GOV-300 母大腦 master_agencies 查詢發布機關權威資訊"""
    resolver = get_mother_gov_resolver()
    try:
        conn = resolver.get_domain_core_db_connection("GOV-300", "master_agencies")
        cursor = conn.cursor()
        cursor.execute("SELECT agency_name, agency_oid, parent_oid FROM master_agencies WHERE agency_oid = ?", (agency_oid,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"agency_name": row[0], "agency_oid": row[1], "parent_oid": row[2]}
    except Exception as e:
        # 當實體檔案尚未載入或路徑例外時優雅 fallback
        pass
    return {"agency_name": "金融監督管理委員會", "agency_oid": agency_oid, "parent_oid": "2.16.886.101.20003"}
