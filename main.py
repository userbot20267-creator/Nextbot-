# main.py

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, ADMIN_ID
import database as db

# استيراد جميع المعالجات
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

# إعداد التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ---------- معالج الأخطاء العام ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء وإرسال تنبيه للمالك عند حدوث خطأ غير متوقع"""
    logger.error(msg="حدث خطأ أثناء معالجة تحديث:", exc_info=context.error)

    # إرسال تنبيه للمالك (اختياري)
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
    # تهيئة قاعدة البيانات
    db.init_db()
    logger.info("✅ تم التحقق من جداول قاعدة البيانات")
    # إرسال رسالة للمالك بأن البوت يعمل
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
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # --- تسجيل أوامر المستخدم الأساسية ---
    application.add_handler(start_handler)
    for handler in user_command_handlers:
        application.add_handler(handler)

    # --- تسجيل معالجات Callback الأساسية (من start) ---
    for handler in start_callback_handlers:
        application.add_handler(handler)

    # --- تسجيل معالجات التصفح (browse) ---
    for handler in browse_handlers:
        application.add_handler(handler)

    # --- تسجيل معالجات الاشتراك الإجباري ---
    for handler in subscription_handlers:
        application.add_handler(handler)

    # --- تسجيل محادثة البحث ---
    application.add_handler(search_conversation_handler)
    for handler in search_callback_handlers:
        application.add_handler(handler)

    # --- تسجيل لوحة تحكم المالك ---
    application.add_handler(admin_handler)
    for handler in admin_callback_handlers:
        application.add_handler(handler)
    for conv_handler in admin_conversation_handlers:
        application.add_handler(conv_handler)

    # --- تسجيل محادثة التغذية الراجعة (feedback) ---
    application.add_handler(feedback_conversation_handler)

    # --- تسجيل معالج الأخطاء العام ---
    application.add_error_handler(error_handler)

    # --- بدء البوت (Polling) ---
    logger.info("🚀 جاري تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
