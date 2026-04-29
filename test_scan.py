import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from action import scan


class TestScanModule(unittest.TestCase):
    def test_classify_complexity(self):
        self.assertEqual(scan.classify_complexity(0), "Low Risk")
        self.assertEqual(scan.classify_complexity(5), "Low Risk")
        self.assertEqual(scan.classify_complexity(6), "Medium Risk")
        self.assertEqual(scan.classify_complexity(10), "Medium Risk")
        self.assertEqual(scan.classify_complexity(11), "High Risk")

    def test_scan_file_returns_function_complexity(self):
        code = """

def example_function(x):
    if x > 0:
        return x
    return 0
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            temp_filename = temp_file.name

        try:
            dummy_block = SimpleNamespace(
                name="example_function",
                complexity=3,
                lineno=1,
            )
            with patch.object(scan, "cc_visit", return_value=[dummy_block]):
                results = scan.scan_file(temp_filename)

            self.assertGreaterEqual(len(results), 1)
            first_result = results[0]
            self.assertEqual(first_result["file"], temp_filename)
            self.assertEqual(first_result["verdict"], "Low Risk")
            self.assertEqual(first_result["function"], "example_function")
            self.assertIn("complexity", first_result)
        finally:
            os.remove(temp_filename)

    def test_build_report_groups_risks(self):
        py_files = ["./action/scan.py"]
        all_results = [
            {"function": "f1", "complexity": 3, "line": 1, "verdict": "Low Risk", "file": "scan.py"},
            {"function": "f2", "complexity": 7, "line": 10, "verdict": "Medium Risk", "file": "scan.py"},
            {"function": "f3", "complexity": 12, "line": 20, "verdict": "High Risk", "file": "scan.py"},
        ]

        report, high, medium, low = scan.build_report(py_files, all_results)
        self.assertIn("Files scanned: 1", report)
        self.assertIn("Functions analysed: 3", report)
        self.assertEqual(len(high), 1)
        self.assertEqual(len(medium), 1)
        self.assertEqual(len(low), 1)
        self.assertIn("High Risk Functions", report)
        self.assertIn("Medium Risk Functions", report)


if __name__ == "__main__":
    unittest.main()
