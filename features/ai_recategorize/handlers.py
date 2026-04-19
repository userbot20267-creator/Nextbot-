# features/ai_recategorize/handlers.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode
from config import ADMIN_ID
from .services import recategorize_books
import database as db


async def ai_recategorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /ai_recategorize
    يعيد تصنيف جميع الكتب الموجودة في قسم 'غير مصنف' تلقائياً
    باستخدام الذكاء الاصطناعي (OpenRouter).
    """
    user_id = update.effective_user.id

    # التحقق من الصلاحية: المالك فقط (أو يمكن إضافة مشرفين)
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمالك والمشرفين فقط.")
        return

    # رسالة انتظار
    msg = await update.message.reply_text(
        "🤖 *جاري تحليل الكتب في قسم 'غير مصنف'...*\n"
        "قد يستغرق هذا بعض الوقت حسب عدد الكتب.",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # استدعاء خدمة إعادة التصنيف
        success, failed = await recategorize_books()

        if success == 0 and failed == 0:
            await msg.edit_text(
                "ℹ️ *لا توجد كتب في قسم 'غير مصنف' حالياً.*",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(
                f"✅ *اكتملت إعادة التصنيف!*\n\n"
                f"📚 تم نقل *{success}* كتاباً إلى أقسامها المناسبة.\n"
                f"❌ فشل نقل *{failed}* كتاباً.\n\n"
                f"يمكنك تفقد قسم 'غير مصنف' للتأكد من الكتب المتبقية.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        await msg.edit_text(
            f"❌ *حدث خطأ أثناء إعادة التصنيف:*\n`{e}`",
            parse_mode=ParseMode.MARKDOWN
        )


def register_handlers(application):
    """تسجيل أمر /ai_recategorize"""
    application.add_handler(CommandHandler("ai_recategorize", ai_recategorize_command))
