# -*- coding: utf-8 -*-
"""
[metadata]
name = date_parser.py
description = 民國年與西元年萬用雙向解析轉換器
category = utils
version = 1.0.0
"""

import re
from typing import Optional

def parse_taiwan_date_universal(raw_val: Optional[str]) -> str:
    """
    全能民國年/西元年萬用日期解析器
    支援格式:
      - '115.08.19' -> '2026-08-19' (點號分隔)
      - '090/11/28' -> '2001-11-28' (斜線分隔)
      - '0771012'   -> '1988-10-12' (7碼無槓純數字)
      - '1150819'   -> '2026-08-19' (7碼無槓純數字)
      - '771012'    -> '1988-10-12' (6碼純數字)
      - '2026-08-19' -> '2026-08-19' (已為 ISO 格式)
      - '2026/08/19' -> '2026-08-19' (西元斜線)
    """
    if not raw_val:
        return ""
        
    s = str(raw_val).strip()
    
    # 格式 1: 已為西元年 YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
        
    # 格式 2: 西元斜線 YYYY/MM/DD 或點號 YYYY.MM.DD
    m_ad = re.match(r"^(\d{4})[./](\d{1,2})[./](\d{1,2})$", s)
    if m_ad:
        y, m, d = m_ad.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        
    # 格式 3: 民國點號或斜線分隔 (如 090/11/28 或 115.08.19 或 90/11/28)
    m_sep = re.match(r"^(\d{2,3})[./-](\d{1,2})[./-](\d{1,2})$", s)
    if m_sep:
        roc_y, m, d = m_sep.groups()
        y = int(roc_y) + 1911
        return f"{y:04d}-{int(m):02d}-{int(d):02d}"
        
    # 格式 4: 緊密 7 碼純數字 (如 0901128 或 1150819)
    if len(s) == 7 and s.isdigit():
        y = int(s[:3]) + 1911
        m = s[3:5]
        d = s[5:7]
        return f"{y:04d}-{m}-{d}"
        
    # 格式 5: 緊密 6 碼純數字 (如 901128)
    if len(s) == 6 and s.isdigit():
        y = int(s[:2]) + 1911
        m = s[2:4]
        d = s[4:6]
        return f"{y:04d}-{m}-{d}"
        
    # 格式 6: 僅有年月 (如 112/05 或 112-05)
    m_ym = re.match(r"^(\d{2,3})[./-](\d{1,2})$", s)
    if m_ym:
        roc_y, m = m_ym.groups()
        y = int(roc_y) + 1911
        return f"{y:04d}-{int(m):02d}"
        
    # 格式 7: 緊密 5 碼純數字年月 (如 11507 -> 2026-07)
    if len(s) == 5 and s.isdigit():
        y = int(s[:3]) + 1911
        m = int(s[3:5])
        return f"{y:04d}-{m:02d}"
        
    return s
