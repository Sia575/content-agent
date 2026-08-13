"""Run one daily-report cycle from the repository root."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hotspot_agent.scheduler.daily_job import DailyRunner
from hotspot_agent.shared.config import load_settings
from export_report_html import export_latest_report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    report_path = DailyRunner(load_settings()).run()
    html_path = export_latest_report()
    print(report_path)
    print(html_path)
