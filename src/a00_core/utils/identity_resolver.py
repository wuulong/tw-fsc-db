# -*- coding: utf-8 -*-
"""
[metadata]
name = identity_resolver.py
description = 台灣法人 8 碼統一編號 (tax_id) 檢查碼演演演演演演演演演演演演算法與格式標準化
category = utils
version = 1.0.0
"""

import re
from typing import Optional, Tuple

WEIGHTS = [1, 2, 1, 2, 1, 2, 4, 1]

def validate_tax_id(tax_id: Optional[str]) -> bool:
    """
    驗證台灣 8 碼統一編號是否符合財政部檢查碼邏輯 (含新舊版乘積相加商數除 10 規則)
    """
    if not tax_id:
        return False
    s = str(tax_id).strip()
    if not (len(s) == 8 and s.isdigit()):
        return False
        
    digits = [int(c) for c in s]
    
    # 乘上權重
    products = [digits[i] * WEIGHTS[i] for i in range(8)]
    
    # 將乘積之十位數與個位數相加
    def sum_digits(n: int) -> int:
        return (n // 10) + (n % 10)
        
    sum_first7 = sum(sum_digits(p) for p in products[:6]) + sum_digits(products[7])
    
    # 第 7 位處理 (權重為 4，若第 7 碼為 7，乘積為 28，位數相加為 10，依規定可為 1 或 0)
    p6 = products[6] # 第 7 碼 (index 6)
    s6 = sum_digits(p6)
    
    if (sum_first7 + s6) % 10 == 0:
        return True
        
    if digits[6] == 7 and (sum_first7 + ((s6 // 10) + (s6 % 10))) % 10 == 0:
        return True
        
    return False

def format_tax_id(tax_id: Optional[str]) -> Optional[str]:
    """格式化統一編號為 8 碼標準字串，若不符格式則回傳 None 或原清洗字串"""
    if not tax_id:
        return None
    s = str(tax_id).strip()
    if len(s) == 8 and s.isdigit():
        return s
    return None
