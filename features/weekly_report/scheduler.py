# features/weekly_report/scheduler.py
import datetime
from .reporter import send_weekly_report

async def weekly_report_callback(context):
    await send_weekly_report(context.bot)

def schedule_weekly_report(application):
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_daily(
            weekly_report_callback,
            time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc),
            days_of_week=(6,),  # تم التعديل: days -> days_of_week
            name="weekly_report"
        )
