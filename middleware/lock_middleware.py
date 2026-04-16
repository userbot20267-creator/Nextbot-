# middleware/lock_middleware.py

from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_lock import is_bot_locked, get_lock_reason
from config import ADMIN_ID
import database as db


async def lock_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    وسيط (Middleware) يفحص حالة القفل قبل معالجة التحديث.
    يرجع True إذا كان مسموحاً بالمعالجة، False إذا تم حظر التحديث.
    """
    if not is_bot_locked():
        return True  # مسموح

    # نستثني الأوامر الإدارية
    if update.message and update.message.text:
        command = update.message.text.split()[0].lower()
        if command in ["/lock", "/unlock", "/lockstatus"]:
            return True

    user_id = update.effective_user.id if update.effective_user else None

    # المالك والمساعدون مسموح لهم دائماً
    if user_id:
        if user_id == ADMIN_ID:
            return True
        if db.is_admin(user_id):
            return True

    # حظر المستخدمين العاديين
    reason = get_lock_reason()
    if update.message:
        await update.message.reply_text(
            f"🔒 *البوت تحت الصيانة حالياً*\n\n"
            f"السبب: {reason}\n\n"
            f"يرجى المحاولة لاحقاً.",
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.answer(
            f"البوت تحت الصيانة: {reason}",
            show_alert=True
        )

    return False  # ممنوع
