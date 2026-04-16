import os
import subprocess
import datetime
import logging
from telegram import Bot
from config import BOT_TOKEN, ADMIN_ID, DATABASE_URL

async def run_backup():
    """Performs a database backup and sends it to the admin."""
    if not DATABASE_URL or not BOT_TOKEN:
        logging.error("DATABASE_URL or BOT_TOKEN not set for backup.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = f"backup_{timestamp}.sql"
    
    try:
        # PostgreSQL pg_dump command (assuming DATABASE_URL is accessible)
        # On Railway, this might need specific environment setup
        command = f"pg_dump {DATABASE_URL} > {backup_file}"
        subprocess.run(command, shell=True, check=True)
        
        # Send backup file to admin via Telegram
        bot = Bot(token=BOT_TOKEN)
        with open(backup_file, 'rb') as f:
            await bot.send_document(
                chat_id=ADMIN_ID, 
                document=f, 
                caption=f"📦 **نسخة احتياطية تلقائية لقاعدة البيانات**\n🗓️ التاريخ: {timestamp}",
                parse_mode="Markdown"
            )
            
        # Clean up
        os.remove(backup_file)
        logging.info(f"Backup {backup_file} sent and deleted.")
        
    except Exception as e:
        logging.error(f"Error during backup: {str(e)}")

# This can be scheduled in main.py using:
# application.job_queue.run_daily(run_backup, time=datetime.time(hour=4, minute=0)) # Run daily at 4 AM
