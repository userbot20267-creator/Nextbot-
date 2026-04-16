# handlers/admin_auto.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID
import database as db
from services.auto_fetcher import fetch_and_add_books


async def fetch_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /fetchnow لجلب الكتب فوراً"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_books", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return

    await update.message.reply_text("⏳ *جاري جلب الكتب من Internet Archive...*", parse_mode=ParseMode.MARKDOWN)
    added = await fetch_and_add_books(context.bot)
    await update.message.reply_text(f"✅ *تم جلب {added} كتاباً جديداً.*", parse_mode=ParseMode.MARKDOWN)


async def toggle_auto_fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /autofetch on/off لتفعيل/تعطيل الجلب التلقائي"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    if not context.args:
        await update.message.reply_text("❌ استخدم: /autofetch on أو /autofetch off")
        return

    state = context.args[0].lower()
    if state == "on":
        db.set_auto_fetch_enabled(True)
        await update.message.reply_text("✅ *تم تفعيل الجلب التلقائي اليومي.*", parse_mode=ParseMode.MARKDOWN)
    elif state == "off":
        db.set_auto_fetch_enabled(False)
        await update.message.reply_text("❌ *تم تعطيل الجلب التلقائي.*", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ استخدم: /autofetch on أو /autofetch off")


admin_auto_handlers = [
    CommandHandler("fetchnow", fetch_now_command),
    CommandHandler("autofetch", toggle_auto_fetch_command),
      ]
