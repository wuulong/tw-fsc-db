# -*- coding: utf-8 -*-
"""
[metadata]
name = sync_guard.py
description = 全庫通用智慧同步防護器 (Smart Sync Guard)，支援 HTTP ETag/Last-Modified 檢驗與檔案 SHA-256 雜湊智慧跳過機制
category = utils
version = 1.0.0
"""

import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Union, Dict, Any, Tuple, Optional

def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """計算檔案之 SHA-256 雜湊值 (Hash)"""
    p = Path(file_path)
    if not p.exists():
        return ""
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def check_remote_header_modified(
    url: str,
    etag: str = "",
    last_modified: str = ""
) -> Tuple[bool, Dict[str, str]]:
    """
    發送 HTTP HEAD 請求檢查遠端檔案 ETag / Last-Modified 標頭。
    返回: (是否需要下載/有變更, 最新標頭資訊)
    """
    headers = {"User-Agent": "tw-fsc-db Smart Sync Guard/1.0"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_etag = response.headers.get("ETag", "").strip('"')
            res_lm = response.headers.get("Last-Modified", "")
            return True, {"etag": res_etag, "last_modified": res_lm}
    except urllib.error.HTTPError as e:
        if e.code == 304:
            # 遠端未修改 ➔ 智慧跳過
            return False, {"etag": etag, "last_modified": last_modified}
        return True, {}
    except Exception:
        # 連線失敗或不支援 HEAD 請求時，保守策略返回有變更，交由 Hash 關卡攔截
        return True, {}

def should_skip_update_by_hash(
    current_file_path: Union[str, Path],
    recorded_sha256: str
) -> Tuple[bool, str, str]:
    """
    以檔案 SHA-256 內容雜湊比對是否與既有紀錄一致。
    返回: (是否跳過, 當前雜湊值, 說明原因)
    """
    p = Path(current_file_path)
    if not p.exists():
        return False, "", "來源檔案不存在，無法比對"

    curr_hash = compute_file_sha256(p)
    if recorded_sha256 and recorded_sha256 == curr_hash:
        return True, curr_hash, f"⚡ 內容 SHA-256 雜湊一致 ({curr_hash[:8]}...)，資料無變更，跳過重覆入庫！"

    return False, curr_hash, "資料內容有更新，執行補充式增量入庫"
