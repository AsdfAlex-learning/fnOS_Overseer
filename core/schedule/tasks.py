from core.report.daily_report import DailyReportBuilder
from core.report.static_renderer import StaticReportRenderer

def run_daily_report():
    data = DailyReportBuilder().build()
    StaticReportRenderer().save(data)
