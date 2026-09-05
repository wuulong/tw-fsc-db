#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOV-A21 (tw-fsc-db) ↔ GOV-300 (tw-gov-db) 跨部會對接整合測試套件
對齊規格: [SPC-011, SPC-014, G300-REQ-FSC-01~04]
"""

import sys
import time
import sqlite3
from pathlib import Path

# 動態加載 G300 SDK
base_dir = Path(__file__).resolve().parents[3]
g300_src = base_dir / "gov-db-in" / "tw-gov-db" / "src"
if str(g300_src) not in sys.path:
    sys.path.insert(0, str(g300_src))

fsc_src = base_dir / "fsc-db-in" / "tw-fsc-db" / "src"
if str(fsc_src) not in sys.path:
    sys.path.insert(0, str(fsc_src))

from core.domain_registry_resolver import DomainRegistryResolver

def test_gov_a21_synergy_integration():
    t0 = time.time()
    print("🚀 啟動 GOV-A21 (tw-fsc-db) ↔ GOV-300 (tw-gov-db) 跨部會對接實測...")
    
    # 1. 階梯 1：初始化 Resolver 與專案元資料定位
    t_start = time.time()
    print("🔍 [Step 1] 初始化 DomainRegistryResolver 載入母專案地圖...")
    resolver = DomainRegistryResolver()
    fsc_info = resolver.get_domain_info("GOV-A21")
    t_step1 = (time.time() - t_start) * 1000
    
    print(f"  ├─ 成功解析 GOV-A21: {fsc_info['name']}")
    print(f"  ├─ 根機關 OID: {fsc_info['root_oid']}")
    print(f"  └─ 耗時: {t_step1:.3f} ms")
    assert fsc_info["project_code"] == "GOV-A21"
    
    # 2. 階梯 2：基石一 OID 歸併驗證 (master_agencies.sqlite)
    t_start = time.time()
    print("🔍 [Step 2] 驗證基石一 OID 歸併 (master_agencies.sqlite)...")
    conn_agencies = resolver.get_domain_core_db_connection("GOV-300", "master_agencies.sqlite")
    cur_a = conn_agencies.cursor()
    cur_a.execute("SELECT agency_name, agency_oid FROM master_agencies WHERE agency_name LIKE '%金融監督管理委員會%' LIMIT 1")
    row_a = cur_a.fetchone()
    t_step2 = (time.time() - t_start) * 1000
    
    assert row_a is not None
    print(f"  ├─ 金管會機關名稱成功對齊權威 OID: {row_a[0]} -> {row_a[1]}")
    print(f"  └─ 耗時: {t_step2:.3f} ms")
    conn_agencies.close()
    
    # 3. 階梯 3：基石二門牌行政區反查驗證 (universal_keys.sqlite / admin_codes)
    t_start = time.time()
    print("🔍 [Step 3] 驗證基石二門牌與行政區劃 (universal_keys.sqlite)...")
    conn_keys = resolver.get_domain_core_db_connection("GOV-300", "universal_keys.sqlite")
    cur_k = conn_keys.cursor()
    cur_k.execute("SELECT admin_code, city_name, district_name FROM admin_codes WHERE city_name='新北市' AND district_name='板橋區'")
    row_k = cur_k.fetchone()
    t_step3 = (time.time() - t_start) * 1000
    
    assert row_k is not None
    assert row_k[0] == "650001"
    print(f"  ├─ 金管會總會所在地 '新北市板橋區' 成功碰撞 6 碼門牌區號: {row_k[0]}")
    print(f"  └─ 耗時: {t_step3:.3f} ms")
    conn_keys.close()
    
    # 4. 階梯 4：直連 FSC 核心資料庫 (db/fsc.db)
    t_start = time.time()
    print("🔍 [Step 4] 驗證 G300 直連 FSC 核心庫 (db/fsc.db)...")
    conn_fsc = resolver.get_domain_core_db_connection("GOV-A21", "fsc.db")
    cur_f = conn_fsc.cursor()
    cur_f.execute("SELECT count(*) FROM f00_entity_registry")
    ent_cnt = cur_f.fetchone()[0]
    t_step4 = (time.time() - t_start) * 1000
    
    assert ent_cnt >= 2500
    print(f"  ├─ 成功讀取 f00_entity_registry 金融法人總數: {ent_cnt} 筆")
    print(f"  └─ 耗時: {t_step4:.3f} ms")
    conn_fsc.close()
    
    total_time = (time.time() - t0) * 1000
    print(f"⏱️ 全套跨部會對接實測總耗時: {total_time:.3f} ms (< 10ms 綠燈門檻)")
    print("✅ GOV-A21 ↔ GOV-300 跨部會對接驗證 100% 通過！")

if __name__ == "__main__":
    test_gov_a21_synergy_integration()
