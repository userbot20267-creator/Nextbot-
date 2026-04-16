# handlers/admin_search.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import database as db
from config import ADMIN_ID
from keyboards import (
    admin_panel_keyboard,
    cancel_only_keyboard,
)
from services.scraper import search_external_books_enhanced, download_file_from_url


# ---------- دوال مساعدة ----------
async def admin_only(update: Update) -> bool:
    """التحقق من صلاحية المالك"""
    if update.effective_user.id != ADMIN_ID:
        if update.callback_query:
            await update.callback_query.answer("⛔ غير مصرح لك.", show_alert=True)
        return False
    return True


def ensure_uncategorized_category() -> int:
    """يتأكد من وجود قسم 'غير مصنف' ويعيد معرفه"""
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    db.add_category("غير مصنف")
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    return 1


# ---------- دوال البحث والإضافة (خاصة بالمالك) ----------
async def admin_search_add_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية البحث عن كتاب خارجي"""
    query = update.callback_query
    await query.answer()
    if not await admin_only(update):
        return ConversationHandler.END

    await query.edit_message_text(
        "🔍 *أرسل اسم الكتاب + المؤلف (بالعربية أو الإنجليزية):*\n\n"
        "سيتم البحث في Internet Archive والمصادر الخارجية وعرض النتائج.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return 0  # WAITING_SEARCH_QUERY (سيتم تعريف الحالة محلياً)


async def admin_search_add_book_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال نص البحث وعرض النتائج مع الغلاف"""
    query_text = update.message.text.strip()
    await update.message.reply_text("🔎 *جاري البحث في المصادر الخارجية...*", parse_mode=ParseMode.MARKDOWN)

    results = await search_external_books_enhanced(query_text, limit=5)

    if not results:
        await update.message.reply_text("❌ لم يتم العثور على نتائج.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    context.user_data["search_results"] = results
    context.user_data["result_index"] = 0

    title, author, link, cover_url = results[0]

    # محاولة تحميل الملف تلقائياً
    tmp_path = await download_file_from_url(link)
    file_id = None
    if tmp_path:
        try:
            with open(tmp_path, 'rb') as f:
                msg = await update.message.reply_document(document=f)
                file_id = msg.document.file_id
            os.unlink(tmp_path)
        except:
            pass

    context.user_data["downloaded_file_id"] = file_id
    context.user_data["current_cover_url"] = cover_url

    # إرسال صورة الغلاف إذا وجدت
    if cover_url:
        try:
            await update.message.reply_photo(photo=cover_url, caption=f"📖 *{title}*\n✍️ {author}")
        except:
            pass

    keyboard = [
        [InlineKeyboardButton("➕ إضافة هذا الكتاب", callback_data="admin_add_search_result")],
        [InlineKeyboardButton("➡️ التالي", callback_data="admin_next_search_result")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_search")],
    ]
    await update.message.reply_text(
        f"📖 *{title}*\n✍️ {author}\n🔗 {link}\n\nالنتيجة 1 من {len(results)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return 0  # حالة الانتظار


async def admin_search_result_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """التنقل بين نتائج البحث وإضافة الكتاب"""
    query = update.callback_query
    await query.answer()

    if query.data == "admin_cancel_search":
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    results = context.user_data.get("search_results", [])
    index = context.user_data.get("result_index", 0)

    if query.data == "admin_next_search_result":
        index = (index + 1) % len(results)
        context.user_data["result_index"] = index
        title, author, link, cover_url = results[index]

        # تحميل الملف
        tmp_path = await download_file_from_url(link)
        file_id = None
        if tmp_path:
            try:
                with open(tmp_path, 'rb') as f:
                    msg = await query.message.reply_document(document=f)
                    file_id = msg.document.file_id
                os.unlink(tmp_path)
            except:
                pass
        context.user_data["downloaded_file_id"] = file_id
        context.user_data["current_cover_url"] = cover_url

        # إرسال صورة الغلاف
        if cover_url:
            try:
                await query.message.reply_photo(photo=cover_url, caption=f"📖 *{title}*\n✍️ {author}")
            except:
                pass

        keyboard = [
            [InlineKeyboardButton("➕ إضافة هذا الكتاب", callback_data="admin_add_search_result")],
            [InlineKeyboardButton("➡️ التالي", callback_data="admin_next_search_result")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_search")],
        ]
        await query.edit_message_text(
            f"📖 *{title}*\n✍️ {author}\n🔗 {link}\n\nالنتيجة {index + 1} من {len(results)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == "admin_add_search_result":
        title, author, link, cover_url = results[index]
        file_id = context.user_data.get("downloaded_file_id")

        cat_id = ensure_uncategorized_category()
        success, author_id = db.add_author(author, cat_id)
        if not success:
            authors = db.get_authors_by_category(cat_id)
            author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)

        if author_id:
            db.add_book(title, author_id, file_id=file_id, file_link=link, added_by=ADMIN_ID)

        await query.edit_message_text("✅ تمت إضافة الكتاب بنجاح.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    return 0


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء العملية"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


# ---------- إنشاء محادثة البحث (خاصة بالمالك) ----------
admin_search_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_search_add_book_start, pattern="^admin_search_add_book$")
    ],
    states={
        0: [  # حالة واحدة مبسطة
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_add_book_receive),
            CallbackQueryHandler(admin_search_result_navigation, pattern="^admin_(next_search_result|add_search_result|cancel_search)$"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_action, pattern="^admin_cancel_search$"),
        CommandHandler("cancel", cancel_action),
    ],
)
