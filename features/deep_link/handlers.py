# features/deep_link/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import database as db
from .services import generate_book_deep_link


async def share_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    زر مشاركة الكتاب: يعرض رابطاً عميقاً للمشاركة.
    """
    query = update.callback_query
    await query.answer()

    # استخراج book_id من callback_data (مثال: share_book_123)
    try:
        book_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ معرف الكتاب غير صالح.")
        return

    book = db.get_book_by_id(book_id)
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return

    title = book[1]
    deep_link = generate_book_deep_link(book_id)

    if not deep_link:
        await query.edit_message_text("❌ لم يتم ضبط BOT_USERNAME في الإعدادات.")
        return

    # نص الرسالة
    text = (
        f"📖 *{title}*\n\n"
        f"🔗 *رابط مشاركة الكتاب:*\n"
        f"`{deep_link}`\n\n"
        f"👆 *اضغط على الرابط لنسخه، ثم أرسله لأصدقائك.*\n"
        f"عندما يفتح صديقك الرابط، سيتمكن من تحميل الكتاب مباشرة."
    )

    # زر للعودة للكتاب
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 العودة للكتاب", callback_data=f"book_{book_id}")]
    ])

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


def register_handlers(application):
    """تسجيل معالجات ميزة المشاركة العميقة"""
    application.add_handler(
        CallbackQueryHandler(share_book_callback, pattern="^share_book_")
    )
