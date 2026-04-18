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
    TypeHandler,
)

from config import BOT_TOKEN, ADMIN_ID
import database as db

# ---------- استيراد جميع المعالجات الأساسية ----------
from handlers.start import start_handler, callback_handlers as start_callback_handlers
from handlers.browse import browse_handlers
from handlers.ai_search import ai_search_conv
from handlers.search import search_conversation_handler, search_callback_handlers
from handlers.subscription import subscription_handlers
from handlers.admin import (
    admin_handler,
    admin_callback_handlers,
    admin_conversation_handlers,
    set_feedback_group_command,
)
from handlers.user import (
    user_command_handlers,
    feedback_conversation_handler,
)

# ---------- استيراد الميزات القديمة ----------
from handlers.admin_roles import admin_roles_handlers, admin_roles_conversation
from handlers.admin_lock import admin_lock_handlers
from handlers.admin_channel import admin_channel_handlers
from handlers.admin_auto import admin_auto_handlers
from middleware.lock_middleware import lock_middleware
from services.auto_fetcher import daily_auto_fetch

# ---------- استيراد الميزات الجديدة (المضافة حديثاً) ----------
from middleware.rate_limit_middleware import rate_limit_check
from handlers.favorites import toggle_favorite, show_favorites
from handlers.history import show_history
from handlers.ratings import start_rating, submit_rating
from handlers.ai_handlers import handle_summarize
from handlers.admin_export import export_users_csv
from handlers.points import show_points
from handlers.admin_messages import custom_msg_handler
from handlers.admin_users_list import list_all_users
from handlers.admin_download import admin_download_handler
from services.backup import run_backup

# ---------- استيراد ميزات مجلد features ----------
from features.pdf_summarizer import register_handlers as register_pdf_handlers
from features.similar_books import register_handlers as register_similar_handlers
from features.user_profile import register_handlers as register_profile_handlers   # 🆕
from features.weekly_report import schedule_weekly_report   # 🆕
from features.referral import register_handlers as register_referral_handlers   # 🆕
from features.deep_link import register_handlers as register_deep_link_handlers
from features.auto_description import register_handlers as register_desc_handlers      # 🆕
from features.auto_category import register_handlers as register_cat_handlers          # 🆕
from features.reminders import schedule_reminders                                      # 🆕
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

    # جدولة المهام الدورية
job_queue = application.job_queue
if job_queue:
    # 1. جدولة مهمة يومية للجلب التلقائي (الساعة 3 صباحاً بالتوقيت العالمي)
    job_queue.run_daily(
        daily_auto_fetch,
        time=datetime.time(hour=3, minute=0, tzinfo=datetime.timezone.utc),
        name="daily_auto_fetch"
    )
    logger.info("✅ تمت جدولة مهمة الجلب اليومي")

    # 2. جدولة النسخ الاحتياطي التلقائي (الساعة 4 صباحاً بالتوقيت العالمي)
    job_queue.run_daily(
        run_backup,
        time=datetime.time(hour=4, minute=0, tzinfo=datetime.timezone.utc),
        name="auto_backup"
    )
    logger.info("✅ تمت جدولة مهمة النسخ الاحتياطي اليومي")

    # 3. جدولة التقرير الأسبوعي (كل يوم أحد 9 صباحاً)
    schedule_weekly_report(application)
    logger.info("✅ تمت جدولة التقرير الأسبوعي")
    # 4. جدولة تذكيرات الكتب غير المكتملة 🆕
     schedule_reminders(application)
     logger.info("✅ تمت جدولة تذكيرات الكتب غير المكتملة")

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

    # --- تسجيل الوسائط (Middleware) ---
    # تسجيل وسيط حماية Rate Limit في المجموعة -2 (يعمل قبل الكل)
    application.add_handler(TypeHandler(Update, rate_limit_check), group=-2)
    
    # تسجيل وسيط القفل كـ TypeHandler في المجموعة -1 (يعمل ثانياً)
    application.add_handler(TypeHandler(Update, lock_middleware), group=-1)

    # --- تسجيل المعالجات الأساسية ---
    application.add_handler(start_handler)
    for handler in user_command_handlers:
        application.add_handler(handler)
    for handler in start_callback_handlers:
        application.add_handler(handler)
    for handler in browse_handlers:
        application.add_handler(handler)
    for handler in subscription_handlers:
        application.add_handler(handler)
    application.add_handler(ai_search_conv)
    application.add_handler(search_conversation_handler)
    for handler in search_callback_handlers:
        application.add_handler(handler)

    application.add_handler(admin_handler)
    for handler in admin_callback_handlers:
        application.add_handler(handler)
    for conv_handler in admin_conversation_handlers:
        application.add_handler(conv_handler)

    application.add_handler(feedback_conversation_handler)

    # --- تسجيل معالجات الميزات السابقة ---
    for handler in admin_roles_handlers:
        application.add_handler(handler)
    application.add_handler(admin_roles_conversation)

    for handler in admin_lock_handlers:
        application.add_handler(handler)

    for handler in admin_channel_handlers:
        application.add_handler(handler)

    for handler in admin_auto_handlers:
        application.add_handler(handler)

    # --- تسجيل معالجات الميزات الجديدة المضافة حديثاً ---
    # 1. أوامر المستخدم الجديدة
    application.add_handler(CommandHandler(["me", "points"], show_points))
    
    # 2. معالجات Callback للمستخدم (المفضلة، السجل، التقييم، التلخيص)
    application.add_handler(CallbackQueryHandler(show_favorites, pattern="^my_favorites$"))
    application.add_handler(CallbackQueryHandler(toggle_favorite, pattern="^toggle_favorite_"))
    application.add_handler(CallbackQueryHandler(show_history, pattern="^my_history$"))
    application.add_handler(CallbackQueryHandler(start_rating, pattern="^rate_book_"))
    application.add_handler(CallbackQueryHandler(submit_rating, pattern="^rate_"))
    # معالج أولوية لتنزيل الكتب الخارجية للمالك (يعمل قبل معالجات admin.py)
    application.add_handler(admin_download_handler, group=1)
    application.add_handler(CallbackQueryHandler(handle_summarize, pattern="^summarize_book_"))
    
    # 3. معالجات الإدمن الجديدة (قائمة المستخدمين، تصدير CSV، تخصيص الرسائل)
    application.add_handler(CallbackQueryHandler(list_all_users, pattern="^admin_users_list$"))
    application.add_handler(CallbackQueryHandler(export_users_csv, pattern="^admin_export_users$"))
    application.add_handler(custom_msg_handler)  # ConversationHandler
    # --- تسجيل معالجات ميزات مجلد features ---
    register_pdf_handlers(application)
    register_similar_handlers(application)
    register_profile_handlers(application)   # 🆕
    register_referral_handlers(application)   # 🆕
    register_deep_link_handlers(application)
    register_desc_handlers(application)   # 🆕
    register_cat_handlers(application)    # 🆕


    # أمر تعيين مجموعة الملاحظات
    application.add_handler(CommandHandler("setfeedbackgroup", set_feedback_group_command))

    application.add_error_handler(error_handler)

    logger.info("🚀 جاري تشغيل البوت...")
    # allowed_updates=Update.ALL_TYPES يسمح للبوت بالعمل في المجموعات أيضاً
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
