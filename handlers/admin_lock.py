# handlers/admin_lock.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID
import database as db

# متغير عالمي لحالة القفل (يفضل استخدام قاعدة البيانات للتخزين الدائم)
_bot_locked = False
_lock_reason = ""


async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /lock لقفل البوت مؤقتاً"""
    user_id = update.effective_user.id

    # التحقق من الصلاحية (مالك أو مساعد بصلاحية إدارة المستخدمين)
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_users", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return

    global _bot_locked, _lock_reason

    args = context.args
    reason = " ".join(args) if args else "الصيانة"

    _bot_locked = True
    _lock_reason = reason

    await update.message.reply_text(
        f"🔒 *تم قفل البوت مؤقتاً*\n\n"
        f"السبب: {reason}\n\n"
        f"لفتح البوت استخدم /unlock",
        parse_mode=ParseMode.MARKDOWN
    )


async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /unlock لفتح البوت"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_users", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return

    global _bot_locked, _lock_reason

    _bot_locked = False
    _lock_reason = ""

    await update.message.reply_text(
        "🔓 *تم فتح البوت وعاد للعمل بشكل طبيعي.*",
        parse_mode=ParseMode.MARKDOWN
    )


async def lock_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /lockstatus لعرض حالة القفل"""
    global _bot_locked, _lock_reason

    if _bot_locked:
        await update.message.reply_text(
            f"🔒 *البوت مقفل حالياً*\nالسبب: {_lock_reason}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "🟢 *البوت مفتوح ويعمل بشكل طبيعي.*",
            parse_mode=ParseMode.MARKDOWN
        )


def is_bot_locked() -> bool:
    """دالة مساعدة لفحص حالة القفل من أي مكان"""
    return _bot_locked


def get_lock_reason() -> str:
    """دالة مساعدة للحصول على سبب القفل"""
    return _lock_reason


# تجميع المعالجات
admin_lock_handlers = [
    CommandHandler("lock", lock_command),
    CommandHandler("unlock", unlock_command),
    CommandHandler("lockstatus", lock_status_command),
          ]
