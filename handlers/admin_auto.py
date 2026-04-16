# handlers/admin_auto.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode
from config import ADMIN_ID
import database as db
from services.auto_fetcher import fetch_and_add_books

async def fetch_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_books", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return
    await update.message.reply_text("⏳ جاري جلب الكتب...")
    added = await fetch_and_add_books(context.bot)
    await update.message.reply_text(f"✅ تم جلب {added} كتاباً.")

async def toggle_auto_fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ للمالك فقط.")
        return
    if not context.args or context.args[0] not in ["on", "off"]:
        await update.message.reply_text("❌ استخدم: /autofetch on/off")
        return
    enabled = context.args[0] == "on"
    db.set_auto_fetch_enabled(enabled)
    await update.message.reply_text(f"✅ الجلب التلقائي: {'مفعل' if enabled else 'معطل'}")

admin_auto_handlers = [
    CommandHandler("fetchnow", fetch_now_command),
    CommandHandler("autofetch", toggle_auto_fetch_command),
]
