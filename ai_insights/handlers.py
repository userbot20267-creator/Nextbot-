# ai_insights/handlers.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode
from config import ADMIN_ID
from .services import get_library_stats, generate_insights

async def ai_insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /ai_insights للمالك فقط - تحليل ذكي للمكتبة"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    msg = await update.message.reply_text("🔍 *جاري جمع إحصائيات المكتبة...*", parse_mode=ParseMode.MARKDOWN)
    
    stats = await get_library_stats()
    
    await msg.edit_text("🤖 *جاري تحليل البيانات بالذكاء الاصطناعي (Gemini)...*", parse_mode=ParseMode.MARKDOWN)
    
    insights = await generate_insights(stats)
    
    # تقسيم الرسالة إذا كانت طويلة جداً
    if len(insights) > 4000:
        for i in range(0, len(insights), 4000):
            await update.message.reply_text(insights[i:i+4000], parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.edit_text(insights, parse_mode=ParseMode.MARKDOWN)

def register_handlers(application):
    """تسجيل أمر /ai_insights"""
    application.add_handler(CommandHandler("ai_insights", ai_insights_command))
