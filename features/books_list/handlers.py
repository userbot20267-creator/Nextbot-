# features/books_list/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import database as db
from config import ADMIN_ID

# عدد الكتب المعروضة في الصفحة الواحدة
BOOKS_PER_PAGE = 10


async def list_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /books - عرض قائمة بجميع الكتب (للمالك والمشرفين)"""
    user_id = update.effective_user.id

    # التحقق من الصلاحية: المالك أو مشرف له صلاحية إدارة الكتب
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمالك والمشرفين فقط.")
        return

    await show_books_page(update, context, page=0)


async def show_books_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """عرض صفحة معينة من قائمة الكتب"""
    offset = page * BOOKS_PER_PAGE
    
    try:
        books = db.get_books_paginated(limit=BOOKS_PER_PAGE, offset=offset)
        total_books = db.count_books()
    except Exception as e:
        error_text = f"❌ حدث خطأ أثناء جلب الكتب: {e}"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return
    
    total_pages = (total_books + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE if total_books > 0 else 1

    if not books:
        text = "📭 لا توجد كتب في المكتبة حالياً."
    else:
        text = f"📚 *جميع الكتب (صفحة {page + 1} من {total_pages})*\n\n"
        for book in books:
            book_id = book[0]
            title = book[1]
            author = book[5] if len(book) > 5 else "غير معروف"
            category = book[6] if len(book) > 6 else "غير مصنف"
            text += f"🆔 `{book_id}` | 📖 {title}\n✍️ {author} | 📁 {category}\n\n"

    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"books_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f"books_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
async def books_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار التنقل بين صفحات الكتب"""
    query = update.callback_query
    await query.answer()

    # التحقق من الصلاحية مرة أخرى (للمالك والمشرفين)
    user_id = query.from_user.id
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح لك.")
        return

    try:
        page = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        page = 0

    await show_books_page(update, context, page)


def register_handlers(application):
    """تسجيل معالجات ميزة عرض جميع الكتب"""
    application.add_handler(CommandHandler("books", list_books_command))
    application.add_handler(CallbackQueryHandler(books_page_callback, pattern="^books_page_"))
