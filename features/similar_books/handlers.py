# features/similar_books/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from .services import get_similar_books


async def show_similar_books_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة بالكتب المشابهة عند الضغط على الزر"""
    query = update.callback_query
    await query.answer()

    # استخراج book_id من callback_data (similar_books_123)
    try:
        book_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ معرف الكتاب غير صالح.")
        return

    similar = get_similar_books(book_id, limit=5)

    if not similar:
        await query.answer("📭 لا توجد كتب مشابهة في هذا القسم حالياً.", show_alert=True)
        return

    # بناء لوحة المفاتيح
    keyboard = []
    for b_id, title, author in similar:
        keyboard.append([
            InlineKeyboardButton(f"📖 {title} - {author}", callback_data=f"book_{b_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 إغلاق", callback_data="delete_message")])

    await query.message.reply_text(
        "📚 *كتب مشابهة قد تعجبك:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delete_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف رسالة الكتب المشابهة"""
    query = update.callback_query
    await query.answer()
    await query.message.delete()


def register_handlers(application):
    """تسجيل معالجات الكتب المشابهة"""
    application.add_handler(
        CallbackQueryHandler(show_similar_books_callback, pattern="^similar_books_")
    )
    application.add_handler(
        CallbackQueryHandler(delete_message_callback, pattern="^delete_message$")
    )
