import tempfile
import unittest
from pathlib import Path

from tools.check_doc_corruption import is_suspicious_question_line, scan_file


class DocCorruptionGuardTests(unittest.TestCase):
    def test_flags_dense_question_mark_line(self):
        self.assertTrue(is_suspicious_question_line("?? ??????? ??????? ?????"))

    def test_does_not_flag_normal_question_line(self):
        self.assertFalse(is_suspicious_question_line("这个脚本怎么使用？"))
        self.assertFalse(is_suspicious_question_line("- 主题："))

    def test_scan_file_reports_utf8_question_corruption(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.md"
            path.write_text("# 标题\n- ??? ????? ???\n", encoding="utf-8")
            issues = scan_file(path)
            self.assertEqual(len(issues), 1)
            self.assertIn("问号", issues[0].reason)

    def test_scan_file_ignores_clean_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "good.md"
            path.write_text("# 标题\n- 这是正常中文内容。\n", encoding="utf-8")
            issues = scan_file(path)
            self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
