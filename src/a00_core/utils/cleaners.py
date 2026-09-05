# -*- coding: utf-8 -*-
"""
[metadata]
name = cleaners.py
description = 通用字串、千分位數值與防呆清洗工具函式庫
category = utils
version = 1.0.0
"""

import re
from typing import Any, Optional

def safe_float(val: Any, default: float = 0.0) -> float:
    """安全轉換浮點數，自動剔除千分位逗號、空白、百分比符號與破折號"""
    if val is None:
        return default
    s = str(val).strip().replace(",", "").replace("%", "").replace(" ", "")
    if s in ("", "-", "--", "N/A", "null", "None"):
        return default
    try:
        return float(s)
    except Exception:
        return default

def safe_int(val: Any, default: int = 0) -> int:
    """安全轉換整數"""
    if val is None:
        return default
    s = str(val).strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "--", "N/A", "null", "None"):
        return default
    try:
        return int(float(s))
    except Exception:
        return default

def clean_text(val: Any) -> str:
    """清洗字串：移除首尾空白、全形空白轉半形、移除不可見控制字元"""
    if val is None:
        return ""
    s = str(val).strip().replace("\u3000", " ")
    # 移除連續空白
    return re.sub(r"\s+", " ", s).strip()
