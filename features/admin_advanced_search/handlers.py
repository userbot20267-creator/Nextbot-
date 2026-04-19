# features/admin_advanced_search/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters
)
from telegram.constants import ParseMode
import database as db
from config import ADMIN_ID
from keyboards import cancel_only_keyboard, admin_panel_keyboard

# حالات المحادثة
WAITING_SEARCH_QUERY = 1


def _get_book_field(book, index, default=""):
    """استخراج حقل من كتاب سواء كان قاموساً أو tuple/list"""
    if isinstance(book, dict):
        if index == 0:
            return book.get('id') or book.get('book_id') or default
        elif index == 1:
            return book.get('title') or default
        elif index == 5:
            return book.get('author') or book.get('author_name') or default
        elif index == 6:
            return book.get('category') or book.get('category_name') or default
        else:
            return default
    else:
        if len(book) > index:
            return book[index]
        return default


async def advanced_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البحث المتقدم - عرض قائمة الفلاتر"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح.")
        return ConversationHandler.END

    context.user_data["adv_filters"] = {
        "category_id": None,
        "author_id": None,
        "date_from": None,
        "date_to": None,
        "file_type": None,
        "has_description": None
    }

    keyboard = build_filter_keyboard(context.user_data["adv_filters"])
    await query.edit_message_text(
        "🔍 *بحث متقدم*\n\nحدد الفلاتر التي تريدها، ثم اضغط 'بحث'.\n"
        "يمكنك البحث بدون تحديد أي فلتر للحصول على جميع الكتب.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    return WAITING_SEARCH_QUERY


def build_filter_keyboard(filters: dict) -> InlineKeyboardMarkup:
    """بناء لوحة مفاتيح الفلاتر بناءً على القيم الحالية"""
    cat_name = "الكل"
    if filters.get('category_id'):
        cat_data = db.get_category_by_id(filters['category_id'])
        if cat_data:
            cat_name = cat_data[1] if isinstance(cat_data, (tuple, list)) and len(cat_data) > 1 else cat_data.get('name', 'غير معروف')
    cat_text = f"📁 القسم: {cat_name}"

    author_name = "الكل"
    if filters.get('author_id'):
        auth_data = db.get_author_by_id(filters['author_id'])
        if auth_data:
            author_name = auth_data[1] if isinstance(auth_data, (tuple, list)) and len(auth_data) > 1 else auth_data.get('name', 'غير معروف')
    author_text = f"✍️ المؤلف: {author_name}"

    date_text = "📅 التاريخ: "
    if filters.get('date_from') and filters.get('date_to'):
        date_text += f"{filters['date_from']} → {filters['date_to']}"
    elif filters.get('date_from'):
        date_text += f"من {filters['date_from']}"
    elif filters.get('date_to'):
        date_text += f"حتى {filters['date_to']}"
    else:
        date_text += "الكل"

    file_text = "📎 النوع: "
    if filters.get('file_type') == 'pdf':
        file_text += "PDF فقط"
    elif filters.get('file_type') == 'link':
        file_text += "روابط فقط"
    else:
        file_text += "الكل"

    desc_text = "📝 وصف: "
    if filters.get('has_description') is True:
        desc_text += "يوجد وصف"
    elif filters.get('has_description') is False:
        desc_text += "بدون وصف"
    else:
        desc_text += "الكل"

    keyboard = [
        [InlineKeyboardButton(cat_text, callback_data="filter_cat")],
        [InlineKeyboardButton(author_text, callback_data="filter_author")],
        [InlineKeyboardButton(date_text, callback_data="filter_date")],
        [InlineKeyboardButton(file_text, callback_data="filter_file")],
        [InlineKeyboardButton(desc_text, callback_data="filter_desc")],
        [
            InlineKeyboardButton("🔍 بحث", callback_data="filter_search"),
            InlineKeyboardButton("🗑 مسح الفلاتر", callback_data="filter_clear")
        ],
        [InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الفلاتر"""
    query = update.callback_query
    await query.answer()
    data = query.data
    filters = context.user_data.get("adv_filters", {})

    if data == "filter_cat":
        categories = db.get_all_categories()
        keyboard = [[InlineKeyboardButton(name, callback_data=f"set_cat_{cid}")] for cid, name in categories]
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="back_to_filters")])
        await query.edit_message_text("اختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("set_cat_"):
        cat_id = int(data.split("_")[-1])
        filters["category_id"] = cat_id
        filters["author_id"] = None
        context.user_data["adv_filters"] = filters
        await back_to_filters(update, context)
    elif data == "filter_author":
        cat_id = filters.get("category_id")
        if not cat_id:
            await query.answer("حدد القسم أولاً", show_alert=True)
            return
        authors = db.get_authors_by_category(cat_id)
        if not authors:
            await query.answer("لا يوجد مؤلفون في هذا القسم", show_alert=True)
            return
        keyboard = [[InlineKeyboardButton(name, callback_data=f"set_auth_{aid}")] for aid, name in authors]
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="back_to_filters")])
        await query.edit_message_text("اختر المؤلف:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("set_auth_"):
        author_id = int(data.split("_")[-1])
        filters["author_id"] = author_id
        context.user_data["adv_filters"] = filters
        await back_to_filters(update, context)
    elif data == "filter_date":
        # تم إزالة إدخال التاريخ النصي
        await query.answer("⏳ ميزة البحث بالتاريخ غير متاحة حالياً.", show_alert=True)
        return WAITING_SEARCH_QUERY
    elif data == "filter_file":
        keyboard = [
            [InlineKeyboardButton("الكل", callback_data="set_file_all")],
            [InlineKeyboardButton("PDF فقط", callback_data="set_file_pdf")],
            [InlineKeyboardButton("روابط فقط", callback_data="set_file_link")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_filters")]
        ]
        await query.edit_message_text("اختر نوع الملف:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("set_file_"):
        ftype = data.split("_")[-1]
        filters["file_type"] = None if ftype == "all" else ftype
        context.user_data["adv_filters"] = filters
        await back_to_filters(update, context)
    elif data == "filter_desc":
        keyboard = [
            [InlineKeyboardButton("الكل", callback_data="set_desc_all")],
            [InlineKeyboardButton("يوجد وصف", callback_data="set_desc_yes")],
            [InlineKeyboardButton("بدون وصف", callback_data="set_desc_no")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_filters")]
        ]
        await query.edit_message_text("حالة الوصف:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("set_desc_"):
        dtype = data.split("_")[-1]
        if dtype == "all":
            filters["has_description"] = None
        else:
            filters["has_description"] = (dtype == "yes")
        context.user_data["adv_filters"] = filters
        await back_to_filters(update, context)
    elif data == "filter_clear":
        context.user_data["adv_filters"] = {
            "category_id": None, "author_id": None,
            "date_from": None, "date_to": None,
            "file_type": None, "has_description": None
        }
        await back_to_filters(update, context)
    elif data == "filter_search":
        filters = context.user_data.get("adv_filters", {})
        try:
            books = db.advanced_search_books(
                category_id=filters.get("category_id"),
                author_id=filters.get("author_id"),
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                file_type=filters.get("file_type"),
                has_description=filters.get("has_description")
            )
        except Exception as e:
            await query.answer(f"❌ خطأ في البحث: {e}", show_alert=True)
            return WAITING_SEARCH_QUERY

        if not books:
            await query.edit_message_text("📭 لا توجد كتب تطابق الفلاتر.", reply_markup=admin_panel_keyboard())
        else:
            text = f"📚 *نتائج البحث ({len(books)} كتاب):*\n\n"
            for b in books[:20]:
                book_id = _get_book_field(b, 0)
                title = _get_book_field(b, 1)
                author = _get_book_field(b, 5, "غير معروف")
                text += f"🆔 `{book_id}` | {title} | {author}\n"
            if len(books) > 20:
                text += f"\n... و {len(books)-20} كتاب آخر."
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END
    elif data == "back_to_filters":
        await back_to_filters(update, context)

    return WAITING_SEARCH_QUERY


async def back_to_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى شاشة الفلاتر الرئيسية"""
    query = update.callback_query
    filters = context.user_data.get("adv_filters", {})
    keyboard = build_filter_keyboard(filters)
    await query.edit_message_text(
        "🔍 *بحث متقدم*\n\nحدد الفلاتر التي تريدها، ثم اضغط 'بحث'.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    return WAITING_SEARCH_QUERY


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء البحث المتقدم والعودة للوحة التحكم"""
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


def register_handlers(application):
    """تسجيل محادثة البحث المتقدم"""
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(advanced_search_start, pattern="^admin_advanced_search$")],
        states={
            WAITING_SEARCH_QUERY: [
                CallbackQueryHandler(filter_callback, pattern="^(filter_|set_|back_to_filters)"),
                # تم إزالة MessageHandler الخاص بالتاريخ
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_search, pattern="^cancel_action$"),
            CommandHandler("cancel", cancel_search)
        ]
    )
    application.add_handler(conv)
