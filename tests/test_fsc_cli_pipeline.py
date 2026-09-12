# -*- coding: utf-8 -*-
"""
[metadata]
name = "test_fsc_cli_pipeline.py"
description = "tw-fsc-db CLI (CGS v2.4) 管道輸入與串流輸出之自動化單元測試"
"""

import io
import sys
import json
import unittest
from unittest.mock import patch
from pathlib import Path

# 定位專案路徑
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from a00_core.fsc_core import resolve_pipe_inputs
from cli.fsc_cli import main

class TestFscCliPipeline(unittest.TestCase):

    def test_resolve_pipe_inputs_arg_priority(self):
        """測試命令行引數優先性"""
        res = resolve_pipe_inputs("2881")
        self.assertEqual(res, ["2881"])

    def test_resolve_pipe_inputs_multiline_stdin(self):
        """測試 stdin 多行輸入解析"""
        fake_stdin = io.StringIO("2881\n2882\n  \n2891\n")
        with patch('sys.stdin', fake_stdin):
            res = resolve_pipe_inputs(None)
            self.assertEqual(res, ["2881", "2882", "2891"])

    def test_resolve_pipe_inputs_comma_separated(self):
        """測試 stdin 逗號分隔輸入解析"""
        fake_stdin = io.StringIO("2881, 2882, 2891")
        with patch('sys.stdin', fake_stdin):
            res = resolve_pipe_inputs(None)
            self.assertEqual(res, ["2881", "2882", "2891"])

    def test_resolve_pipe_inputs_json_array(self):
        """測試 stdin JSON Array 輸入解析"""
        fake_stdin = io.StringIO('["2881", "2882"]')
        with patch('sys.stdin', fake_stdin):
            res = resolve_pipe_inputs(None)
            self.assertEqual(res, ["2881", "2882"])

    def test_cli_company_profile_pipeline_json(self):
        """測試 company profile 透過 pipe 傳入並輸出乾淨 JSON"""
        fake_stdin = io.StringIO("2881\n2882\n")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        test_args = ["fsc_cli.py", "company", "profile", "-j"]
        
        with patch('sys.stdin', fake_stdin), patch('sys.argv', test_args), patch('sys.stdout', stdout_buf), patch('sys.stderr', stderr_buf):
            main()
            
        out_str = stdout_buf.getvalue().strip()
        self.assertTrue(len(out_str) > 0)
        parsed = json.loads(out_str)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 2)
        codes = [item["company_code"] for item in parsed]
        self.assertIn("2881", codes)
        self.assertIn("2882", codes)

    def test_cli_search_pipeline_json(self):
        """測試 search 透過 pipe 傳入並輸出乾淨 JSON"""
        fake_stdin = io.StringIO("國泰\n富邦\n")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        test_args = ["fsc_cli.py", "search", "-j", "-n", "2"]
        
        with patch('sys.stdin', fake_stdin), patch('sys.argv', test_args), patch('sys.stdout', stdout_buf), patch('sys.stderr', stderr_buf):
            main()
            
        out_str = stdout_buf.getvalue().strip()
        parsed = json.loads(out_str)
        self.assertIsInstance(parsed, list)
        self.assertTrue(len(parsed) > 0)

if __name__ == "__main__":
    unittest.main()
