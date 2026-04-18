# features/weekly_report/scheduler.py
import datetime
from .reporter import send_weekly_report

async def weekly_report_callback(context):
    """الدالة التي ستستدعى أسبوعياً"""
    await send_weekly_report(context.bot)

def schedule_weekly_report(application):
    """جدولة التقرير الأسبوعي (كل يوم أحد الساعة 9 صباحاً)"""
    job_queue = application.job_queue
    if job_queue:
        # تشغيل كل يوم أحد الساعة 9:00 UTC
        job_queue.run_daily(
            weekly_report_callback,
            time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc),
            days=(6,),  # 6 = Sunday (Monday is 0)
            name="weekly_report"
        )
