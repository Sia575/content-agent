from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from hotspot_agent.scheduler.daily_job import DailyRunner
from hotspot_agent.shared.config import load_settings
from hotspot_agent.shared.time_utils import get_timezone


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    timezone = get_timezone(settings["app"]["timezone"])
    hour, minute = (int(part) for part in settings["app"]["daily_run_time"].split(":"))
    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(
        DailyRunner(settings).run,
        CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="hotspot_daily_report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logging.getLogger(__name__).info("Scheduler started for %02d:%02d Asia/Shanghai", hour, minute)
    scheduler.start()


if __name__ == "__main__":
    main()
