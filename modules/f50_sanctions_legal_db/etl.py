# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F50 法律事務與處分裁罰智庫自包含 ETL (解析 499 筆真實處分書 XML 與評議資料)
category = etl
version = 2.0.0
"""

import os
import sys
import re
import csv
import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from typing import Union, Dict, Any, List
from datetime import datetime
import xml.etree.ElementTree as ET

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from a00_core.udfs import get_connection_with_udfs
from a00_core.metadata_manager import register_submodule_metadata

def _make_uid(prefix: str, *args) -> str:
    raw = "_".join(str(a) for a in args)
    h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{h}"

def _parse_roc_date_from_text(text: str) -> str:
    m = re.search(r'中華民國\s*([0-9]{2,3})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日', text)
    if m:
        yr = int(m.group(1)) + 1911
        mo = int(m.group(2))
        day = int(m.group(3))
        return f"{yr:04d}-{mo:02d}-{day:02d}"
    return "2026-08-01"

def _clean_html_tags(text: str) -> str:
    clean = re.sub(r'<br\s*/?>', '\n', text)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = clean.replace('&nbsp;', ' ').replace('&hellip;', '...').replace('&amp;', '&')
    return re.sub(r'[ \t]+', ' ', clean).strip()

def run_f50_etl(db_path: Union[str, Path],
                sanctions_xml_source: Union[str, Path] = None,
                ombudsman_source: Union[str, Path] = None) -> Dict[str, Any]:
    """
    執行 F50 法律事務、處分裁罰與評議爭議資料清洗入庫
    """
    db_p = Path(db_path)
    db_p.parent.mkdir(parents=True, exist_ok=True)
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    samples_dir = base_dir / "data" / "samples"
    
    if not sanctions_xml_source:
        sanctions_xml_source = raw_dir / "f50_sanctions_rss.xml" if (raw_dir / "f50_sanctions_rss.xml").exists() else samples_dir / "f50_sanctions_rss_sample.xml"
    if not ombudsman_source:
        ombudsman_source = raw_dir / "f51_ombudsman_cases.csv" if (raw_dir / "f51_ombudsman_cases.csv").exists() else samples_dir / "f50_ombudsman_cases_sample.csv"
        
    conn = get_connection_with_udfs(db_p)
    cursor = conn.cursor()
    
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    now_ts = datetime.now().isoformat()
    sanction_rows = []
    fts_rows = []
    
    xml_p = Path(sanctions_xml_source)
    if xml_p.exists():
        tree = ET.parse(xml_p)
        items = tree.getroot().find("channel").findall("item")
        
        for it in items:
            t_elem = it.find("title")
            title = t_elem.text if (t_elem is not None and t_elem.text) else ""
            l_elem = it.find("link")
            link = l_elem.text if (l_elem is not None and l_elem.text) else ""
            d_elem = it.find("description")
            desc = d_elem.text if (d_elem is not None and d_elem.text) else ""
            clean_desc = _clean_html_tags(desc)
            
            # 提取發文字號
            doc_m = re.search(r'發文字號[：:]\s*([^\s\n<]+)', clean_desc)
            doc_no = doc_m.group(1).strip() if doc_m else ""
            if not doc_no:
                t_m = re.search(r'\((金管[^\)]+號)\)', title)
                doc_no = t_m.group(1) if t_m else f"金管處分_{hashlib.md5(title.encode('utf-8')).hexdigest()[:8]}"
                
            # 提取受處分人
            target_m = re.search(r'受處分人[：:]\s*([^\s\n<]+)', clean_desc)
            if target_m:
                target_name = target_m.group(1).strip()
            else:
                target_name = title.split("辦理")[0].split("違反")[0].split("所涉")[0].strip()
                if len(target_name) > 30 or not target_name:
                    target_name = "受處分金融機構"
                    
            # 提取統一編號
            tax_m = re.search(r'營利事業統一編號[：:]\s*([0-9]{8})', clean_desc)
            tax_id = tax_m.group(1) if tax_m else None
            
            s_date = _parse_roc_date_from_text(clean_desc)
            
            # 提取罰鍰金額
            fine_m = re.search(r'([0-9,]+)\s*萬元罰鍰', clean_desc)
            if fine_m:
                fine_w = float(fine_m.group(1).replace(",", ""))
                penalty_fine = fine_w * 10000.0
            else:
                fine_m2 = re.search(r'新臺幣\s*([0-9,]+)\s*元罰鍰', clean_desc)
                penalty_fine = float(fine_m2.group(1).replace(",", "")) if fine_m2 else 0.0
                
            bureau = "銀行局"
            if "金管銀" in doc_no:
                bureau = "銀行局"
            elif "金管證" in doc_no:
                bureau = "證券期貨局"
            elif "金管保" in doc_no:
                bureau = "保險局"
            elif "金管檢" in doc_no:
                bureau = "檢查局"
                
            main_subj = ""
            violation_facts = ""
            legal_basis = ""
            
            s_subj = re.search(r'主旨[：:]\s*(.*?)(?=事實[：:]|理由及法令依據[：:]|繳款方式[：:]|$)', clean_desc, re.DOTALL)
            if s_subj:
                main_subj = s_subj.group(1).strip()
            else:
                main_subj = title
                
            s_fact = re.search(r'事實[：:]\s*(.*?)(?=理由及法令依據[：:]|繳款方式[：:]|注意事項[：:]|$)', clean_desc, re.DOTALL)
            if s_fact:
                violation_facts = s_fact.group(1).strip()
                
            s_law = re.search(r'理由及法令依據[：:]\s*(.*?)(?=繳款方式[：:]|注意事項[：:]|正本[：:]|$)', clean_desc, re.DOTALL)
            if s_law:
                legal_basis = s_law.group(1).strip()
                
            uid = _make_uid("SNC", doc_no)
            sanction_rows.append((
                uid, doc_no, s_date, target_name, tax_id, penalty_fine, bureau,
                main_subj, violation_facts, legal_basis, link, now_ts
            ))
            fts_rows.append((
                uid, doc_no, target_name, main_subj, violation_facts, legal_basis
            ))
            
    cursor.executemany("""
        INSERT OR REPLACE INTO f50_sanctions
        (sanction_uid, doc_no, sanction_date, target_name, tax_id, penalty_fine_ntd, agency_bureau,
         main_subject, violation_facts, legal_basis, source_url, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sanction_rows)
    
    cursor.execute("DELETE FROM f50_sanctions_fts")
    cursor.executemany("""
        INSERT INTO f50_sanctions_fts
        (sanction_uid, doc_no, target_name, main_subject, violation_facts, legal_basis)
        VALUES (?, ?, ?, ?, ?, ?)
    """, fts_rows)
    
    omb_rows = []
    omb_p = Path(ombudsman_source)
    if omb_p.exists():
        with open(omb_p, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                s_d = str(r.get("日期(起)", "")).strip()
                e_d = str(r.get("日期(迄)", "")).strip()
                inst = str(r.get("爭議對象", "")).strip()
                cnt_str = str(r.get("申訴件數", "0")).strip()
                pct_str = str(r.get("案件比率(註1)", "0")).replace("%", "").strip()
                if not inst:
                    continue
                cnt = int(cnt_str) if cnt_str.isdigit() else 0
                pct = float(pct_str) if pct_str else 0.0
                
                start_iso = f"{s_d[:4]}-{s_d[4:6]}-{s_d[6:]}" if len(s_d) == 8 else "2026-04-01"
                end_iso = f"{e_d[:4]}-{e_d[4:6]}-{e_d[6:]}" if len(e_d) == 8 else "2026-06-30"
                
                uid = _make_uid("OMB", start_iso, end_iso, inst)
                omb_rows.append((
                    uid, start_iso, end_iso, inst, cnt, pct, now_ts
                ))
                
        cursor.executemany("""
            INSERT OR REPLACE INTO f50_ombudsman_cases
            (case_uid, start_date, end_date, institution_name, complaint_count, complaint_ratio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, omb_rows)
        
    conn.commit()
    conn.close()
    
    tables_meta = [
        ("f50_sanctions", len(sanction_rows)),
        ("f50_ombudsman_cases", len(omb_rows))
    ]
    for tbl, count in tables_meta:
        register_submodule_metadata(
            db_p,
            module_id="f50_sanctions_legal_db",
            module_name="法律事務處與處分裁罰智庫",
            table_name=tbl,
            schema_version="2.0.0",
            record_count=count
        )
        
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "sanctions_loaded": len(sanction_rows),
        "ombudsman_cases_loaded": len(omb_rows),
        "fts_indexed": len(fts_rows),
        "executed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F50 法律事務與處分裁罰 ETL 腳本")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    args = parser.parse_args()
    
    if not args.db:
        base_dir = Path(__file__).resolve().parent.parent.parent
        target_db = base_dir / "db" / "fsc.db"
    else:
        target_db = Path(args.db)
        
    res = run_f50_etl(target_db)
    print(json.dumps(res, ensure_ascii=False, indent=2))
