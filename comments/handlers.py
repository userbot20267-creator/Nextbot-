# comments/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, CommandHandler
from telegram.constants import ParseMode
from .services import add_comment, get_book_comments, toggle_like, delete_comment
from .keyboards import comments_menu_keyboard, comment_actions_keyboard
import database as db
from config import ADMIN_ID

WAITING_COMMENT_TEXT = 1

async def show_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تعليقات كتاب معين"""
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    context.user_data["comment_book_id"] = book_id
    
    comments = get_book_comments(book_id, user_id=update.effective_user.id)
    
    if not comments:
        text = "💬 لا توجد تعليقات بعد. كن أول من يعلق!"
    else:
        text = f"💬 *تعليقات القراء:*\n\n"
        for c in comments:
            name = c['first_name'] or f"@{c['username']}" or "مستخدم"
            likes = c['likes_count']
            text += f"👤 {name}:\n{c['text']}\n❤️ {likes} | 🆔 `{c['id']}`\n\n"
    
    keyboard = comments_menu_keyboard(book_id)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def add_comment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة تعليق"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ *أرسل تعليقك على هذا الكتاب:*\n(الحد الأقصى 500 حرف)\nأرسل /cancel للإلغاء.",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_COMMENT_TEXT

async def receive_comment_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال نص التعليق وحفظه"""
    user_id = update.effective_user.id
    book_id = context.user_data.get("comment_book_id")
    text = update.message.text.strip()
    
    comment_id = add_comment(user_id, book_id, text)
    if comment_id:
        await update.message.reply_text("✅ تم إضافة تعليقك!")
    else:
        await update.message.reply_text("❌ فشل إضافة التعليق.")
    
    # العودة لعرض التعليقات
    return await show_comments(update, context)

async def like_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الإعجاب بتعليق"""
    query = update.callback_query
    user_id = update.effective_user.id
    comment_id = int(query.data.split("_")[-1])
    
    liked, count = toggle_like(user_id, comment_id)
    await query.answer(f"❤️ {count}" if liked else f"💔 {count}")

async def delete_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف تعليق (للمالك أو صاحب التعليق)"""
    query = update.callback_query
    user_id = update.effective_user.id
    comment_id = int(query.data.split("_")[-1])
    
    is_admin = (user_id == ADMIN_ID)
    success = delete_comment(comment_id, user_id, is_admin)
    
    if success:
        await query.answer("✅ تم حذف التعليق")
        # تحديث القائمة
        await show_comments(update, context)
    else:
        await query.answer("❌ لا يمكنك حذف هذا التعليق", show_alert=True)

def register_handlers(application):
    """تسجيل معالجات التعليقات"""
    from .models import create_tables
    create_tables()  # إنشاء الجداول عند التحميل
    
    application.add_handler(CallbackQueryHandler(show_comments, pattern="^comments_"))
    application.add_handler(CallbackQueryHandler(like_comment, pattern="^like_comment_"))
    application.add_handler(CallbackQueryHandler(delete_comment_callback, pattern="^delete_comment_"))
    
    comment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_comment_start, pattern="^add_comment$")],
        states={
            WAITING_COMMENT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment_text)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(comment_conv)
