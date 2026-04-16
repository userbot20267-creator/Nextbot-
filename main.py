# main.py

import os
import logging
import threading
import datetime
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
    TypeHandler,          # <-- تمت الإضافة
)

from config import BOT_TOKEN, ADMIN_ID
import database as db

# ---------- استيراد جميع المعالجات الأساسية ----------
from handlers.start import start_handler, callback_handlers as start_callback_handlers
from handlers.browse import browse_handlers
from handlers.search import search_conversation_handler, search_callback_handlers
from handlers.subscription import subscription_handlers
from handlers.admin import (
    admin_handler,
    admin_callback_handlers,
    admin_conversation_handlers,
)
from handlers.user import (
    user_command_handlers,
    feedback_conversation_handler,
)

# ---------- استيراد الميزات الجديدة ----------
from handlers.admin_roles import admin_roles_handlers, admin_roles_conversation
from handlers.admin_lock import admin_lock_handlers
from handlers.admin_channel import admin_channel_handlers
from handlers.admin_auto import admin_auto_handlers
from middleware.lock_middleware import lock_middleware
from services.auto_fetcher import daily_auto_fetch

# ---------- إعداد Flask لفتح منفذ وهمي (لحل مشكلة Web Service) ----------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# ---------- إعداد التسجيل (Logging) ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ---------- معالج الأخطاء العام ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء وإرسال تنبيه للمالك عند حدوث خطأ غير متوقع"""
    logger.error(msg="حدث خطأ أثناء معالجة تحديث:", exc_info=context.error)

    if update and update.effective_user:
        error_message = (
            f"⚠️ *تنبيه خطأ في البوت*\n\n"
            f"👤 المستخدم: {update.effective_user.full_name} (`{update.effective_user.id}`)\n"
            f"📝 التحديث: `{update}`\n\n"
            f"❌ الخطأ: `{context.error}`"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=error_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"فشل في إرسال تنبيه الخطأ للمالك: {e}")


# ---------- دالة بدء التشغيل ----------
async def post_init(application: Application) -> None:
    """تُنفذ بعد تهيئة التطبيق مباشرة"""
    logger.info("✅ تم تهيئة البوت بنجاح")
    db.init_db()
    logger.info("✅ تم التحقق من جداول قاعدة البيانات")

    # جدولة مهمة يومية للجلب التلقائي (الساعة 3 صباحاً بالتوقيت العالمي)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_daily(
            daily_auto_fetch,
            time=datetime.time(hour=3, minute=0, tzinfo=datetime.timezone.utc),
            name="daily_auto_fetch"
        )
        logger.info("✅ تمت جدولة مهمة الجلب اليومي")

    try:
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text="🟢 *تم تشغيل البوت بنجاح!*",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"لم يتم إرسال رسالة بدء التشغيل للمالك: {e}")


# ---------- الدالة الرئيسية ----------
def main() -> None:
    """تشغيل البوت"""
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # تسجيل وسيط القفل كـ TypeHandler في المجموعة -1 (يعمل أولاً)
    application.add_handler(TypeHandler(Update, lock_middleware), group=-1)

    # تسجيل المعالجات الأساسية
    application.add_handler(start_handler)
    for handler in user_command_handlers:
        application.add_handler(handler)
    for handler in start_callback_handlers:
        application.add_handler(handler)
    for handler in browse_handlers:
        application.add_handler(handler)
    for handler in subscription_handlers:
        application.add_handler(handler)

    application.add_handler(search_conversation_handler)
    for handler in search_callback_handlers:
        application.add_handler(handler)

    application.add_handler(admin_handler)
    for handler in admin_callback_handlers:
        application.add_handler(handler)
    for conv_handler in admin_conversation_handlers:
        application.add_handler(conv_handler)

    application.add_handler(feedback_conversation_handler)

    # تسجيل معالجات الميزات الجديدة
    for handler in admin_roles_handlers:
        application.add_handler(handler)
    application.add_handler(admin_roles_conversation)

    for handler in admin_lock_handlers:
        application.add_handler(handler)

    for handler in admin_channel_handlers:
        application.add_handler(handler)

    for handler in admin_auto_handlers:
        application.add_handler(handler)

    application.add_error_handler(error_handler)

    logger.info("🚀 جاري تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
