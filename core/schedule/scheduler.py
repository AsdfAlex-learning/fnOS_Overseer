import importlib
from zoneinfo import ZoneInfo
from core.schedule.tasks import run_daily_report
from core.config.config_manager import get_value

def create_scheduler(timezone: str = "Asia/Shanghai"):
    bg = importlib.import_module("apscheduler.schedulers.background")
    cron = importlib.import_module("apscheduler.triggers.cron")
    tz = ZoneInfo(timezone) if timezone else None
    scheduler = bg.BackgroundScheduler(timezone=tz)

    # Read report time from config
    report_time_str = get_value("schedule.report_time", "08:00")
    try:
        hour, minute = map(int, report_time_str.split(":"))
    except (ValueError, AttributeError):
        # Fallback to default if parsing fails
        hour, minute = 0, 30

    trigger = cron.CronTrigger(hour=hour, minute=minute, timezone=tz)
    scheduler.add_job(run_daily_report, trigger, id="daily_report", replace_existing=True)
    return scheduler

def start():
    scheduler = create_scheduler()
    scheduler.start()
    return scheduler
