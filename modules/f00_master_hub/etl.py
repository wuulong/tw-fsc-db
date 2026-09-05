# -*- coding: utf-8 -*-
"""
[metadata]
script_name = etl.py
description = F00 全域倒排索引 (FTS5) 聚合、全域實體註冊主表 (f00_entity_registry) 與系統元資料同步
category = etl
version = 2.0.0
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# 引入核心共用庫
src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from a00_core.metadata_manager import register_submodule_metadata

def build_f00_master_index(db_path: Path) -> Dict[str, Any]:
    """
    掃描已入庫之各子模組實體，注入 f00_entity_registry 主表並清空重建全域 FTS5 倒排索引
    """
    db_p = Path(db_path)
    if not db_p.exists():
        return {"status": "SKIPPED", "reason": "資料庫不存在"}
        
    conn = sqlite3.connect(str(db_p))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 確保 F00 Schema 存在 (包含 f00_entity_registry, f00_entity_relations, f00_supervisory_radar, fts_fsc_global)
    schema_p = Path(__file__).parent / "schema.sql"
    if schema_p.exists():
        cursor.executescript(schema_p.read_text(encoding="utf-8"))
        
    # 清空現有倒排索引、實體註冊表與關係拓樸表
    cursor.execute("DELETE FROM fts_fsc_global")
    cursor.execute("DELETE FROM f00_entity_relations")
    cursor.execute("DELETE FROM f00_entity_registry")
    
    total_indexed = 0
    total_entities = 0
    now_ts = datetime.now().isoformat()
    
    # 1. 索引與註冊 F10: 金控公司
    try:
        cursor.execute("SELECT holding_name, group_assets_billion, group_net_worth_billion, subsidiaries_text FROM f10_financial_holdings")
        rows = cursor.fetchall()
        for r in rows:
            h_name = r["holding_name"]
            uid = f"ENT_FHC_{h_name}"
            payload = {
                "assets_billion": r["group_assets_billion"],
                "net_worth_billion": r["group_net_worth_billion"],
                "subsidiaries": r["subsidiaries_text"]
            }
            # 寫入實體主表
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, h_name, h_name.replace("金融控股公司", "金控"), "FHC", 1, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1
            
            # 寫入 FTS5 倒排
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F10", "HOLDING", uid, h_name, r["subsidiaries_text"] or "", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass
        
    # 2. 索引與註冊 F10: 本國商業銀行
    try:
        cursor.execute("SELECT bank_name, loan_total, npl_ratio, coverage_ratio FROM f10_bank_asset_quality")
        rows = cursor.fetchall()
        for r in rows:
            b_name = r["bank_name"]
            uid = f"ENT_BANK_{b_name}"
            payload = {
                "loan_total": r["loan_total"],
                "npl_ratio": r["npl_ratio"],
                "coverage_ratio": r["coverage_ratio"]
            }
            # 寫入實體主表
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, b_name, b_name.replace("商業銀行", "銀行"), "BANK", 1, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            # 寫入 FTS5 倒排
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F10", "BANK", uid, b_name, f"放款: {r['loan_total']}M 逾放比: {r['npl_ratio']}%", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass

    # 3. 索引與註冊 F20: 上市與公開發行公司 (COMPANY)
    try:
        cursor.execute("SELECT company_code, company_name, isin_code, industry_category, market_type FROM f20_companies")
        rows = cursor.fetchall()
        for r in rows:
            c_code = r["company_code"]
            c_name = r["company_name"]
            uid = f"ENT_STOCK_{c_code}"
            payload = {
                "company_code": c_code,
                "isin_code": r["isin_code"],
                "industry": r["industry_category"],
                "market": r["market_type"]
            }
            # 寫入實體主表
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, stock_code, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, c_code, c_name, c_name, "LISTED", 0, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            # 寫入 FTS5 倒排
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F20", "COMPANY", uid, c_name, f"產業: {r['industry_category']} | 代號: {c_code} | 市場: {r['market_type']}", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass

    # 4. 索引與註冊 F20: 上櫃股票公司與市場估值 (VALUATION)
    try:
        cursor.execute("SELECT company_code, company_name, pe_ratio, dividend_yield, pb_ratio FROM f20_market_valuations")
        val_rows = cursor.fetchall()
        for vr in val_rows:
            v_code = vr["company_code"]
            v_name = vr["company_name"]
            uid = f"ENT_STOCK_{v_code}"
            payload = {
                "company_code": v_code,
                "pe_ratio": vr["pe_ratio"],
                "dividend_yield": vr["dividend_yield"],
                "pb_ratio": vr["pb_ratio"]
            }
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, stock_code, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, v_code, v_name, v_name, "LISTED_OTC", 0, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F20", "VALUATION", uid, v_name, f"上櫃股票 | 代號: {v_code} | 殖利率: {vr['dividend_yield']}% | P/E: {vr['pe_ratio']}", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass


    # 5. 索引與註冊 F30: 保險機構 (INSURER)
    try:
        cursor.execute("SELECT insurer_name, insurer_type, inner_staff_count, field_agent_count, underwriting_count, claim_count, actuary_count FROM f30_insurance_institutions")
        ins_rows = cursor.fetchall()
        for ir in ins_rows:
            i_name = ir["insurer_name"]
            uid = f"ENT_INS_{i_name}"
            payload = {
                "insurer_name": i_name,
                "insurer_type": ir["insurer_type"],
                "actuary_count": ir["actuary_count"],
                "underwriting_count": ir["underwriting_count"],
                "claim_count": ir["claim_count"]
            }
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, i_name, i_name.replace("保險股份有限公司", "").replace("股份有限公司", ""), "INSURER", 1, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            type_zh = "人壽保險" if ir["insurer_type"] == "LIFE" else ("產物保險" if ir["insurer_type"] == "PROPERTY" else "保險機構")
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F30", "INSURER", uid, i_name, f"類型: {type_zh} | 精算: {ir['actuary_count']}人 | 核保: {ir['underwriting_count']}人 | 理賠: {ir['claim_count']}人", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass


    # 6. 建置跨模組集團股權與子公司控制力拓樸 (F10 金控 -> F10/F20/F30 子公司)
    total_relations = 0
    try:
        # 先抓取當前所有註冊實體字典以利秒級快速匹配
        cursor.execute("SELECT master_uid, canonical_name, common_alias, entity_class FROM f00_entity_registry")
        all_ents = cursor.fetchall()
        
        cursor.execute("SELECT holding_name, subsidiaries_text FROM f10_financial_holdings")
        fhc_rows = cursor.fetchall()
        for fhc in fhc_rows:
            h_name = fhc["holding_name"]
            p_uid = f"ENT_FHC_{h_name}"
            raw_text = (fhc["subsidiaries_text"] or "").replace(",", "、").replace("，", "、")
            subs = [s.strip() for s in raw_text.split("、") if s.strip()]
            
            for s in subs:
                matched_child_uid = None
                clean_s = s.replace("股份有限公司", "").replace("公司", "").strip()
                
                # 遍歷尋找最相符的子實體
                for ent in all_ents:
                    e_uid = ent["master_uid"]
                    if e_uid == p_uid:
                        continue
                    c_name = ent["canonical_name"]
                    alias = ent["common_alias"] or ""
                    
                    if s == c_name or clean_s == alias or clean_s in c_name:
                        matched_child_uid = e_uid
                        break
                        
                # 若未在持牌機構中比對到 (例如 華南金資產管理、富邦創投、國泰投信)，則動態補登為 AFFILIATE 實體
                if not matched_child_uid:
                    matched_child_uid = f"ENT_AFF_{s}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO f00_entity_registry 
                        (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (matched_child_uid, s, clean_s, "AFFILIATE", 1, now_ts, now_ts, json.dumps({"parent_fhc": h_name}, ensure_ascii=False)))
                    total_entities += 1
                    
                    cursor.execute("""
                        INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("F10", "AFFILIATE", matched_child_uid, s, f"隸屬金融集團: {h_name} | 金控子公司", json.dumps({"parent_fhc": h_name}, ensure_ascii=False)))
                    total_indexed += 1
                
                # 寫入控制力關係邊
                rel_uid = f"REL_{p_uid}_{matched_child_uid}_SUB"
                cursor.execute("""
                    INSERT OR REPLACE INTO f00_entity_relations
                    (relation_uid, parent_uid, child_uid, relation_type, shareholding_ratio, control_level, effective_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (rel_uid, p_uid, matched_child_uid, "SUBSIDIARY", 100.0, "DIRECT", "2026-09-05", now_ts))
                total_relations += 1
    except sqlite3.OperationalError:
        pass

    # 7. 建置持股逾 10% 大股東拓樸關聯 (F20 大股東 -> 公開發行公司)
    try:
        cursor.execute("""
            SELECT company_code, company_name, shareholder_name, is_corporate, report_date
            FROM f20_major_shareholders
        """)
        sh_rows = cursor.fetchall()
        for sh in sh_rows:
            c_code = sh["company_code"]
            child_uid = f"ENT_STOCK_{c_code}"
            sh_name = sh["shareholder_name"].strip()
            if not sh_name:
                continue
                
            parent_uid = f"ENT_SH_{sh_name}"
            # 註冊大股東實體 (若不存在)
            cursor.execute("""
                INSERT OR IGNORE INTO f00_entity_registry 
                (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (parent_uid, sh_name, sh_name, "MAJOR_SHAREHOLDER", 0, now_ts, now_ts, json.dumps({"is_corporate": sh["is_corporate"]}, ensure_ascii=False)))
            total_entities += 1
            
            rel_uid = f"REL_{parent_uid}_{child_uid}_MAJ"
            cursor.execute("""
                INSERT OR REPLACE INTO f00_entity_relations
                (relation_uid, parent_uid, child_uid, relation_type, shareholding_ratio, control_level, effective_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (rel_uid, parent_uid, child_uid, "MAJOR_SHAREHOLDER", 10.0, "DIRECT", sh["report_date"], now_ts))
            total_relations += 1
    except sqlite3.OperationalError:
        pass

    # 8. 索引 F40: 金融檢查重大缺失 (INSPECTION)
    try:
        cursor.execute("SELECT deficiency_uid, target_sector, business_category, deficiency_pattern, deficiency_detail FROM f40_exam_deficiencies")
        f40_rows = cursor.fetchall()
        for d in f40_rows:
            uid = d["deficiency_uid"]
            sec = d["target_sector"]
            pat = d["deficiency_pattern"]
            det = d["deficiency_detail"] or ""
            cat = d["business_category"]
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F40", "INSPECTION", uid, pat, f"類別: {cat} | 對象: {sec} | 情節: {det[:120]}", json.dumps({"uid": uid, "sector": sec, "category": cat}, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass

    # 9. 索引 F50: 重大行政裁處處分書 (SANCTION)
    try:
        cursor.execute("SELECT sanction_uid, doc_no, target_name, main_subject, violation_facts, penalty_fine_ntd FROM f50_sanctions")
        f50_rows = cursor.fetchall()
        for s in f50_rows:
            uid = s["sanction_uid"]
            t_name = s["target_name"]
            d_no = s["doc_no"]
            subj = s["main_subject"]
            fact = s["violation_facts"] or ""
            fine = s["penalty_fine_ntd"] or 0.0
            cursor.execute("""
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("F50", "SANCTION", uid, f"{t_name} ({d_no})", f"主旨: {subj[:100]} | 罰鍰: {fine:,.0f}元 | 事實: {fact[:120]}", json.dumps({"uid": uid, "doc_no": d_no, "target": t_name, "fine": fine}, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass

    # 10. 索引與註冊 F60: 虛擬資產平台業者 (VASP) 與金融科技沙盒 (FINTECH)
    try:
        # VASP 名冊
        cursor.execute("SELECT vasp_id, brand_name, company_name, tax_id, compliance_date, business_type, fiat_custody_bank, status FROM f60_vasp_compliance_registry")
        vasp_rows = cursor.fetchall()
        for v in vasp_rows:
            v_id = v["vasp_id"]
            c_name = v["company_name"]
            b_name = v["brand_name"]
            t_id = v["tax_id"]
            fiat = v["fiat_custody_bank"] or "無"
            uid = f"ENT_VASP_{v_id}"
            payload = {
                "vasp_id": v_id,
                "brand_name": b_name,
                "company_name": c_name,
                "tax_id": t_id,
                "business_type": v["business_type"],
                "fiat_custody_bank": fiat,
                "status": v["status"]
            }
            cursor.execute('''
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, tax_id, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (uid, t_id, c_name, b_name, "VASP", 0, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            cursor.execute('''
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ("F60", "VASP", uid, f"{b_name} ({c_name})", f"統編: {t_id} | 業務: {v['business_type']} | 信託銀行: {fiat} | 狀態: {v['status']}", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1

        # 沙盒創新實驗
        cursor.execute("SELECT case_no, applicant, partner_institution, experiment_title, experiment_domain, status FROM f60_fintech_sandbox")
        sb_rows = cursor.fetchall()
        for sb in sb_rows:
            c_no = sb["case_no"]
            app = sb["applicant"]
            partner = sb["partner_institution"]
            title = sb["experiment_title"]
            dom = sb["experiment_domain"]
            uid = f"ENT_SANDBOX_{c_no}"
            payload = {
                "case_no": c_no,
                "applicant": app,
                "partner_institution": partner,
                "experiment_title": title,
                "status": sb["status"]
            }
            cursor.execute('''
                INSERT OR REPLACE INTO f00_entity_registry 
                (master_uid, canonical_name, common_alias, entity_class, is_financial_institution, created_at, updated_at, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (uid, app, app.replace("科技股份有限公司", "").replace("證券投資顧問股份有限公司", ""), "FINTECH_SANDBOX", 0, now_ts, now_ts, json.dumps(payload, ensure_ascii=False)))
            total_entities += 1

            cursor.execute('''
                INSERT INTO fts_fsc_global (domain_code, entity_type, entity_id, primary_name, secondary_info, detail_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ("F60", "SANDBOX", uid, f"{app} - {title}", f"合作特許銀行: {partner} | 案號: {c_no} | 領域: {dom} | 狀態: {sb['status']}", json.dumps(payload, ensure_ascii=False)))
            total_indexed += 1
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    
    # 登記 F00 自身元資料
    register_submodule_metadata(
        db_p,
        module_id="f00_master_hub",
        module_name="金管會母大腦全域倒排與元資料治理中心",
        table_name="fts_fsc_global",
        schema_version="2.0.0",
        record_count=total_indexed
    )
    register_submodule_metadata(
        db_p,
        module_id="f00_master_hub",
        module_name="金管會母大腦全域倒排與元資料治理中心",
        table_name="f00_entity_registry",
        schema_version="2.0.0",
        record_count=total_entities
    )
    register_submodule_metadata(
        db_p,
        module_id="f00_master_hub",
        module_name="金管會母大腦全域倒排與元資料治理中心",
        table_name="f00_entity_relations",
        schema_version="2.0.0",
        record_count=total_relations
    )
    
    return {
        "status": "SUCCESS",
        "target_db": str(db_p),
        "total_entities_registered": total_entities,
        "total_entities_indexed": total_indexed,
        "total_relations_built": total_relations,
        "indexed_at": now_ts
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F00 全域倒排索引建置與聚合腳本")
    parser.add_argument("--db", default=None, help="目標 SQLite 資料庫路徑")
    args = parser.parse_args()
    
    if not args.db:
        base_dir = Path(__file__).resolve().parent.parent.parent
        target_db = base_dir / "db" / "fsc.db"
    else:
        target_db = Path(args.db)
        
    res = build_f00_master_index(target_db)
    print(json.dumps(res, ensure_ascii=False, indent=2))
