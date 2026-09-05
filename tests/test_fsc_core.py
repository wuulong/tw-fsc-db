# -*- coding: utf-8 -*-
"""
金融監督管理委員會 與 GOV-300 母大腦連鎖單元測試
"""

import sys
from pathlib import Path

def test_gov_mother_connection():
    """測試是否能成功引用 GOV-300 母大腦通用 Library"""
    parent_src = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(parent_src))
    
    from a00_core.fsc_core import get_mother_gov_resolver, query_agency_base_info
    resolver = get_mother_gov_resolver()
    assert resolver is not None
    info = query_agency_base_info("2.16.886.101.20003.20022")
    assert info["agency_name"] == "金融監督管理委員會"
    print("✅ 成功引用 GOV-300 母大腦通用 Library 並驗證金管會資訊，測試綠燈！")

if __name__ == "__main__":
    test_gov_mother_connection()
