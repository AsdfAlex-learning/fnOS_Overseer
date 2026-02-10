import importlib
from zoneinfo import ZoneInfo
from core.schedule.tasks import run_daily_report

def create_scheduler(timezone: str = "Asia/Shanghai"):
    bg = importlib.import_module("apscheduler.schedulers.background")
    cron = importlib.import_module("apscheduler.triggers.cron")
    tz = ZoneInfo(timezone) if timezone else None
    scheduler = bg.BackgroundScheduler(timezone=tz)
    trigger = cron.CronTrigger(hour=0, minute=30, timezone=tz)
    scheduler.add_job(run_daily_report, trigger, id="daily_report", replace_existing=True)
    return scheduler

def start():
    scheduler = create_scheduler()
    scheduler.start()
    return scheduler
