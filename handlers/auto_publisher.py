# handlers/admin_channel.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID
import database as db


async def set_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /setchannel لتعيين قناة النشر التلقائي"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_manage_categories", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return

    if not context.args:
        await update.message.reply_text(
            "❌ *استخدم:* `/setchannel @username` أو `/setchannel -100123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    channel_id = context.args[0]
    try:
        # التحقق من وجود القناة وأن البوت مضاف كمسؤول
        chat = await context.bot.get_chat(channel_id)
        db.set_channel_id(channel_id)
        await update.message.reply_text(
            f"✅ *تم تعيين قناة النشر التلقائي:*\n{chat.title}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *تعذر الوصول للقناة:* تأكد أن البوت مضاف كمسؤول.\nخطأ: {e}",
            parse_mode=ParseMode.MARKDOWN
        )


async def get_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /getchannel لعرض القناة الحالية"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        perms = db.get_admin_permissions(user_id)
        if not perms.get("can_view_stats", False):
            await update.message.reply_text("⛔ غير مصرح لك.")
            return

    channel_id = db.get_channel_id()
    if not channel_id:
        await update.message.reply_text("❌ لم يتم تعيين قناة بعد. استخدم /setchannel")
        return

    try:
        chat = await context.bot.get_chat(channel_id)
        await update.message.reply_text(
            f"📢 *القناة الحالية:* {chat.title} (`{channel_id}`)",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await update.message.reply_text(f"📢 *معرف القناة:* `{channel_id}`", parse_mode=ParseMode.MARKDOWN)


admin_channel_handlers = [
    CommandHandler("setchannel", set_channel_command),
    CommandHandler("getchannel", get_channel_command),
]
