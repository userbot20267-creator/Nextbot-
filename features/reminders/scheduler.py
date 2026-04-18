import datetime
from .reporter import send_reminders

async def reminder_callback(context):
    await send_reminders(context.bot)

def schedule_reminders(application):
    job_queue = application.job_queue
    if job_queue:
        # تشغيل كل يومين عند الساعة 10 صباحاً
        job_queue.run_daily(
            reminder_callback,
            time=datetime.time(hour=10, minute=0, tzinfo=datetime.timezone.utc),
            days=(0, 2, 4, 6),  # كل يومين
            name="incomplete_books_reminder"
        )
