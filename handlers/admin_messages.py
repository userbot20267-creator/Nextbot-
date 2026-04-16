from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from database import get_connection
from config import ADMIN_ID

SET_MSG_TYPE, SET_MSG_CONTENT = range(2)

async def start_custom_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
        
    await update.message.reply_text(
        "📝 **تخصيص رسائل البوت:**\n\n"
        "يرجى إرسال اسم الرسالة التي تريد تعديلها (مثلاً: `welcome_msg` أو `help_msg`):",
        parse_mode="Markdown"
    )
    return SET_MSG_TYPE

async def set_msg_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['msg_type'] = update.message.text
    await update.message.reply_text(
        f"✅ حسناً، أرسل الآن المحتوى الجديد لرسالة `{update.message.text}`:",
        parse_mode="Markdown"
    )
    return SET_MSG_CONTENT

async def save_custom_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_type = context.user_data.get('msg_type')
    new_content = update.message.text
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings (key, value) 
                VALUES (%s, %s) 
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (msg_type, new_content))
            conn.commit()
            
    await update.message.reply_text(f"✅ تم تحديث الرسالة `{msg_type}` بنجاح!")
    return ConversationHandler.END

async def cancel_custom_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء عملية تخصيص الرسائل.")
    return ConversationHandler.END

custom_msg_handler = ConversationHandler(
    entry_points=[CommandHandler("setmsg", start_custom_msg)],
    states={
        SET_MSG_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_msg_type)],
        SET_MSG_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_custom_msg)],
    },
    fallbacks=[CommandHandler("cancel", cancel_custom_msg)],
    per_message=True # Add per_message=True as requested in fixes
)

# Register handler in main.py:
# application.add_handler(custom_msg_handler)
