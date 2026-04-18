# features/user_profile/handlers.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from .services import get_user_stats
import database as db


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /profile أو /me لعرض الملف الشخصي للمستخدم.
    """
    user = update.effective_user
    user_id = user.id
    
    # تحديث آخر نشاط
    db.update_activity(user_id)
    
    # جلب الإحصائيات
    stats = get_user_stats(user_id)
    
    # تنسيق تاريخ الانضمام
    if stats["joined"]:
        joined_str = stats["joined"].strftime("%Y-%m-%d")
    else:
        joined_str = "غير معروف"
    
    # بناء نص الرسالة
    text = (
        f"👤 *الملف الشخصي*\n\n"
        f"🆔 *المعرف:* `{user_id}`\n"
        f"👤 *الاسم:* {user.full_name}\n"
    )
    
    if user.username:
        text += f"📎 *اليوزر:* @{user.username}\n"
    
    text += (
        f"📅 *تاريخ الانضمام:* {joined_str}\n\n"
        f"📊 *إحصائياتك:*\n"
        f"📥 *الكتب المحملة:* {stats['downloads']}\n"
        f"❤️ *المفضلة:* {stats['favorites']}\n"
        f"🏆 *النقاط:* {stats['points']}\n"
    )
    
    if stats["badges"]:
        badges_text = "  ".join(stats["badges"])
        text += f"\n🎖️ *الشارات:*\n{badges_text}"
    else:
        text += "\n🎖️ *الشارات:* لا توجد بعد - حمل المزيد من الكتب!"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def register_handlers(application):
    """
    تسجيل معالجات الملف الشخصي.
    """
    # نسجل /profile و /me (سيحل محل show_points القديم تدريجياً)
    application.add_handler(CommandHandler(["profile", "me"], profile_command))
