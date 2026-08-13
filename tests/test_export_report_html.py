from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from export_report_html import export_latest_report, export_latest_workbench, find_latest_markdown
from run_content_agent import _format_body_for_markdown


class ExportReportHtmlTests(unittest.TestCase):
    def test_finds_latest_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            older = output_dir / "hotspot-daily-2026-08-11.md"
            newer = output_dir / "hotspot-daily-2026-08-12.md"
            older.write_text("# Older\n", encoding="utf-8")
            time.sleep(0.01)
            newer.write_text("# Newer\n", encoding="utf-8")
            self.assertEqual(find_latest_markdown(output_dir), newer)

    def test_exports_latest_report_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report = output_dir / "hotspot-daily-2026-08-12.md"
            report.write_text(
                "# 内容报告\n\n"
                "## 国际科技新闻\n\n"
                "- 来源：[The Verge](https://www.theverge.com/)\n\n"
                "| 字段 | 值 |\n"
                "| --- | --- |\n"
                "| score | 90 |\n",
                encoding="utf-8",
            )
            html_path = export_latest_report(output_dir)
            content = html_path.read_text(encoding="utf-8")
            self.assertEqual(html_path, output_dir / "latest-report.html")
            self.assertIn("内容报告", content)
            self.assertIn("The Verge", content)
            self.assertIn("score", content)

    def test_exports_latest_workbench_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            workbench = output_dir / "latest-workbench.md"
            workbench.write_text("# 内容工作台\n\n## 选题\n\n正文内容\n", encoding="utf-8")
            html_path = export_latest_workbench(output_dir)
            content = html_path.read_text(encoding="utf-8")
            self.assertEqual(html_path, output_dir / "latest-workbench.html")
            self.assertIn("<title>内容工作台</title>", content)
            self.assertIn("正文内容", content)
            self.assertIn("内容运营 Agent · 内容工作台", content)
            self.assertIn("作者：靳思嘉", content)
            self.assertNotIn("**", content)

    def test_formats_standalone_hashtag_line_as_label(self) -> None:
        body = "正文\n\n#AI工具 #内容运营"

        rendered = _format_body_for_markdown(body)

        self.assertEqual(rendered, "正文\n\n标签：#AI工具 #内容运营")


if __name__ == "__main__":
    unittest.main()
