# handlers/admin_channel.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode
from config import ADMIN_ID
import database as db

async def set_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_categories", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return
    if not context.args:
        await update.message.reply_text("❌ استخدم: /setchannel @username")
        return
    channel_id = context.args[0]
    try:
        chat = await context.bot.get_chat(channel_id)
        db.set_channel_id(channel_id)
        await update.message.reply_text(f"✅ تم تعيين القناة: {chat.title}")
    except Exception as e:
        await update.message.reply_text(f"❌ تعذر الوصول: {e}")

async def get_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_id = db.get_channel_id()
    if not channel_id:
        await update.message.reply_text("❌ لم يتم تعيين قناة.")
        return
    await update.message.reply_text(f"📢 القناة الحالية: {channel_id}")

admin_channel_handlers = [
    CommandHandler("setchannel", set_channel_command),
    CommandHandler("getchannel", get_channel_command),
]
