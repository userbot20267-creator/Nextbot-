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


async def advanced_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البحث المتقدم - عرض قائمة الفلاتر"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح.")
        return ConversationHandler.END

    # تهيئة قاموس الفلاتر
    context.user_data["adv_filters"] = {
        "category_id": None,
        "author_id": None,
        "date_from": None,
        "date_to": None,
        "file_type": None,      # "pdf" أو "link"
        "has_description": None # True/False
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
    # نص القسم
    cat_text = f"📁 القسم: {db.get_category_by_id(filters['category_id'])[1] if filters['category_id'] else 'الكل'}"
    # نص المؤلف
    author_text = f"✍️ المؤلف: {db.get_author_by_id(filters['author_id'])[1] if filters['author_id'] else 'الكل'}"
    # نص التاريخ
    date_text = "📅 التاريخ: "
    if filters['date_from'] and filters['date_to']:
        date_text += f"{filters['date_from']} → {filters['date_to']}"
    elif filters['date_from']:
        date_text += f"من {filters['date_from']}"
    elif filters['date_to']:
        date_text += f"حتى {filters['date_to']}"
    else:
        date_text += "الكل"
    # نص نوع الملف
    file_text = "📎 النوع: "
    if filters['file_type'] == 'pdf':
        file_text += "PDF فقط"
    elif filters['file_type'] == 'link':
        file_text += "روابط فقط"
    else:
        file_text += "الكل"
    # نص الوصف
    desc_text = "📝 وصف: "
    if filters['has_description'] is True:
        desc_text += "يوجد وصف"
    elif filters['has_description'] is False:
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
        # عند تغيير القسم، يتم إعادة تعيين المؤلف
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
        await query.edit_message_text(
            "أرسل التاريخ بالصيغة: YYYY-MM-DD\n"
            "للبحث من تاريخ: `من 2024-01-01`\n"
            "للبحث حتى تاريخ: `الى 2024-12-31`\n"
            "أو `2024-01-01 2024-12-31` للنطاق الكامل.\n"
            "أرسل /cancel للعودة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_only_keyboard()
        )
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
        books = db.advanced_search_books(
            category_id=filters.get("category_id"),
            author_id=filters.get("author_id"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            file_type=filters.get("file_type"),
            has_description=filters.get("has_description")
        )
        if not books:
            await query.edit_message_text("📭 لا توجد كتب تطابق الفلاتر.", reply_markup=admin_panel_keyboard())
        else:
            text = f"📚 *نتائج البحث ({len(books)} كتاب):*\n\n"
            for b in books[:20]:
                text += f"🆔 `{b[0]}` | {b[1]} | {b[5]}\n"
            if len(books) > 20:
                text += f"\n... و {len(books)-20} كتاب آخر."
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END
    elif data == "back_to_filters":
        await back_to_filters(update, context)
    else:
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


async def receive_date_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال مدخلات التاريخ من المستخدم"""
    text = update.message.text.strip()
    filters = context.user_data.get("adv_filters", {})
    parts = text.split()
    if len(parts) == 2:
        # صيغة "YYYY-MM-DD YYYY-MM-DD"
        filters["date_from"], filters["date_to"] = parts[0], parts[1]
    elif text.startswith("من "):
        filters["date_from"] = text[3:].strip()
        filters["date_to"] = None
    elif text.startswith("الى "):
        filters["date_from"] = None
        filters["date_to"] = text[3:].strip()
    else:
        # تاريخ واحد يعتبر "من"
        filters["date_from"] = text
        filters["date_to"] = None

    context.user_data["adv_filters"] = filters
    await update.message.reply_text("✅ تم تحديد التاريخ.")
    # محاكاة بداية البحث المتقدم للعودة للقائمة
    # نرسل رسالة جديدة مع لوحة الفلاتر
    keyboard = build_filter_keyboard(filters)
    await update.message.reply_text(
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date_filter)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_search, pattern="^cancel_action$"),
            CommandHandler("cancel", cancel_search)
        ]
    )
    application.add_handler(conv)
