import datetime
from apscheduler.triggers.cron import CronTrigger
from .reporter import send_reminders

async def reminder_callback(context):
    await send_reminders(context.bot)

def schedule_reminders(application):
    job_queue = application.job_queue
    if job_queue:
        # تشغيل كل يومين عند الساعة 10 صباحاً (الاثنين، الأربعاء، الجمعة، الأحد)
        job_queue.run_custom(
            reminder_callback,
            trigger=CronTrigger(day_of_week='mon,wed,fri,sun', hour=10, minute=0, timezone=datetime.timezone.utc),
            name="incomplete_books_reminder"
        )
