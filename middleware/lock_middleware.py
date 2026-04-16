# middleware/lock_middleware.py

from telegram import Update
from telegram.ext import BaseHandler, ContextTypes
from handlers.admin_lock import is_bot_locked, get_lock_reason
from config import ADMIN_ID
import database as db


class LockMiddleware:
    """
    وسيط (Middleware) يفحص حالة القفل قبل تنفيذ أي أمر.
    """

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not is_bot_locked():
            return

        # نستثني أوامر القفل والفتح والمالك والمساعدين
        if update.message and update.message.text:
            command = update.message.text.split()[0].lower()
            if command in ["/lock", "/unlock", "/lockstatus"]:
                return

        user_id = update.effective_user.id if update.effective_user else None

        # نسمح للمالك والمساعدين بتجاوز القفل
        if user_id:
            if user_id == ADMIN_ID:
                return
            if db.is_admin(user_id):
                return

        # منع المستخدمين العاديين
        if update.message:
            await update.message.reply_text(
                f"🔒 *البوت تحت الصيانة حالياً*\n\n"
                f"السبب: {get_lock_reason()}\n\n"
                f"يرجى المحاولة لاحقاً.",
                parse_mode="Markdown"
            )
        elif update.callback_query:
            await update.callback_query.answer(
                f"البوت تحت الصيانة: {get_lock_reason()}",
                show_alert=True
            )

        # إلغاء معالجة التحديث
        raise ApplicationHandlerStop
