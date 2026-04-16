import time
from telegram import Update
from telegram.ext import ContextTypes, TypeHandler

# Dictionary to store user request times: {user_id: [timestamp1, timestamp2, ...]}
user_requests = {}

# Settings: 20 requests per minute (adjustable)
RATE_LIMIT = 20
TIME_WINDOW = 60

async def rate_limit_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    
    user_id = update.effective_user.id
    current_time = time.time()
    
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    # Remove timestamps older than the time window
    user_requests[user_id] = [t for t in user_requests[user_id] if current_time - t < TIME_WINDOW]
    
    if len(user_requests[user_id]) >= RATE_LIMIT:
        if update.message:
            await update.message.reply_text(
                "⚠️ **تنبيه حماية:** لقد تجاوزت حد الطلبات المسموح به (20 طلب/دقيقة). يرجى الانتظار قليلاً لتجنب الحظر المؤقت. ⏳",
                parse_mode="Markdown"
            )
        # Stop further processing of this update
        raise Exception("Rate limit exceeded")
    
    user_requests[user_id].append(current_time)

# In main.py, this should be added as:
# application.add_handler(TypeHandler(Update, rate_limit_check), group=-1)
