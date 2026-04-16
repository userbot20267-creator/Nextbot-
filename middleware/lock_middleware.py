# middleware/lock_middleware.py

from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from handlers.admin_lock import is_bot_locked, get_lock_reason
from config import ADMIN_ID
import database as db


async def lock_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يعمل كـ Handler في المجموعة -1.
    إذا كان البوت مقفلاً والمستخدم غير مسموح له، يتم إرسال رسالة ومنع المعالجة.
    """
    # إذا لم يكن البوت مقفلاً، مرر التحديث بشكل طبيعي
    if not is_bot_locked():
        return

    # استثناء: السماح لأوامر القفل نفسها
    if update.message and update.message.text:
        command = update.message.text.split()[0].lower()
        if command in ["/lock", "/unlock", "/lockstatus"]:
            return

    user_id = update.effective_user.id if update.effective_user else None

    # المالك والمساعدون مسموح لهم دائمًا
    if user_id:
        if user_id == ADMIN_ID:
            return
        if db.is_admin(user_id):
            return

    # المستخدم العادي ممنوع
    reason = get_lock_reason()
    if update.message:
        await update.message.reply_text(
            f"🔒 *البوت تحت الصيانة حالياً*\n\nالسبب: {reason}",
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.answer(
            f"البوت تحت الصيانة: {reason}",
            show_alert=True
        )

    # منع باقي المعالجات من استقبال هذا التحديث
    raise ApplicationHandlerStop
