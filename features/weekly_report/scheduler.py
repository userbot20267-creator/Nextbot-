# features/weekly_report/scheduler.py
import datetime
from apscheduler.triggers.cron import CronTrigger
from .reporter import send_weekly_report

async def weekly_report_callback(context):
    """الدالة التي ستستدعى أسبوعياً"""
    await send_weekly_report(context.bot)

def schedule_weekly_report(application):
    """جدولة التقرير الأسبوعي (كل يوم أحد الساعة 9 صباحاً)"""
    job_queue = application.job_queue
    if job_queue:
        # تشغيل كل يوم أحد الساعة 9:00 UTC
        job_queue.run_custom(
            weekly_report_callback,
            trigger=CronTrigger(day_of_week='sun', hour=9, minute=0, timezone=datetime.timezone.utc),
            name="weekly_report"
        )
