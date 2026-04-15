# handlers/admin.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services.scraper import search_external_books
from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import database as db
from config import ADMIN_ID
from keyboards import (
    admin_panel_keyboard,
    admin_categories_keyboard,
    admin_category_actions_keyboard,
    admin_books_management_keyboard,
    admin_users_keyboard,
    admin_channels_keyboard,
    admin_stats_keyboard,
    cancel_only_keyboard,
    confirm_cancel_keyboard,
    main_menu,
)
from utils import broadcast_message

# حالات المحادثة (Conversation States)
(
    # إدارة الأقسام
    WAITING_CATEGORY_NAME,
    WAITING_CATEGORY_EDIT_NAME,
    WAITING_CATEGORY_DELETE_CONFIRM,
    # إدارة الكتب
    WAITING_BOOK_TITLE,
    WAITING_BOOK_AUTHOR,
    WAITING_BOOK_FILE,
    WAITING_BOOK_EDIT_SELECT,
    WAITING_BOOK_EDIT_FIELD,
    WAITING_BOOK_DELETE_CONFIRM,
    # إدارة المستخدمين
    WAITING_BAN_USER_ID,
    WAITING_UNBAN_USER_ID,
    # الإذاعة
    WAITING_BROADCAST_MESSAGE,
    # إدارة القنوات
    WAITING_CHANNEL_USERNAME,
    WAITING_CHANNEL_DELETE_CONFIRM,
) = range(14)


# ---------- دوال مساعدة للتحقق من الصلاحية ----------
def is_admin(update: Update) -> bool:
    """التحقق من أن المستخدم هو المالك"""
    return update.effective_user.id == ADMIN_ID


async def admin_only(update: Update) -> bool:
    """تزيين الدالة للتحقق من الصلاحية مع تنبيه"""
    if not is_admin(update):
        if update.callback_query:
            await update.callback_query.answer("⛔ غير مصرح لك.", show_alert=True)
        return False
    return True


# ---------- أمر /admin ----------
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض لوحة التحكم الرئيسية للمالك"""
    if not is_admin(update):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return

    await update.message.reply_text(
        "🎛 *لوحة تحكم المالك*\n\nاختر أحد الخيارات:",
        reply_markup=admin_panel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ---------- العودة إلى اللوحة الرئيسية ----------
async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للوحة التحكم"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎛 *لوحة تحكم المالك*",
        reply_markup=admin_panel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ---------- معالجات الأقسام ----------
async def admin_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة الأقسام مع خيارات الإدارة"""
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    categories = db.get_all_categories()
    await query.edit_message_text(
        "📁 *إدارة الأقسام*",
        reply_markup=admin_categories_keyboard(categories),
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_category_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض خيارات التعديل/الحذف لقسم محدد"""
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    cat_id = int(query.data.split("_")[2])
    category = db.get_category_by_id(cat_id)
    if not category:
        await query.answer("القسم غير موجود", show_alert=True)
        return

    context.user_data["admin_cat_id"] = cat_id
    await query.edit_message_text(
        f"⚙️ *القسم: {category[1]}*",
        reply_markup=admin_category_actions_keyboard(cat_id),
        parse_mode=ParseMode.MARKDOWN
    )


# --- إضافة قسم ---
async def admin_add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    await query.edit_message_text(
        "📝 *أرسل اسم القسم الجديد:*\n\nأرسل /cancel للإلغاء.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_CATEGORY_NAME


async def admin_add_category_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if db.add_category(name):
        await update.message.reply_text(f"✅ تم إضافة القسم *{name}* بنجاح.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ القسم موجود مسبقاً أو حدث خطأ.")

    await admin_command(update, context)
    return ConversationHandler.END


# --- تعديل قسم ---
async def admin_edit_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    cat_id = int(query.data.split("_")[2])
    context.user_data["edit_cat_id"] = cat_id
    await query.edit_message_text(
        "✏️ *أرسل الاسم الجديد للقسم:*",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_CATEGORY_EDIT_NAME


async def admin_edit_category_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    cat_id = context.user_data.get("edit_cat_id")
    if db.update_category(cat_id, new_name):
        await update.message.reply_text("✅ تم تعديل القسم بنجاح.")
    else:
        await update.message.reply_text("❌ فشل التعديل (قد يكون الاسم موجوداً مسبقاً).")

    await admin_command(update, context)
    return ConversationHandler.END


# --- حذف قسم ---
async def admin_delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    cat_id = int(query.data.split("_")[2])
    context.user_data["del_cat_id"] = cat_id
    await query.edit_message_text(
        "⚠️ *تحذير:* حذف القسم سيؤدي إلى حذف جميع المؤلفين والكتب المرتبطة به.\n\nهل أنت متأكد؟",
        reply_markup=confirm_cancel_keyboard("delcat"),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_CATEGORY_DELETE_CONFIRM


async def admin_delete_category_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data.startswith("confirm_"):
        cat_id = context.user_data.get("del_cat_id")
        db.delete_category(cat_id)
        await query.edit_message_text("✅ تم حذف القسم.", reply_markup=admin_panel_keyboard())
    else:
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


# ---------- إدارة الكتب ----------
async def admin_books_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    await query.edit_message_text(
        "📚 *إدارة الكتب*",
        reply_markup=admin_books_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_add_book_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    # تحميل الأقسام والمؤلفين للاختيار لاحقًا (يمكن استخدام inline)
    # للتبسيط سنطلب إدخال نصي
    await query.edit_message_text(
        "📖 *أرسل عنوان الكتاب:*",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_BOOK_TITLE


async def admin_add_book_title_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["book_title"] = update.message.text.strip()
    await update.message.reply_text(
        "✍️ *أرسل اسم المؤلف:*",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_BOOK_AUTHOR


async def admin_add_book_author_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    author_name = update.message.text.strip()
    # نحتاج لقسم افتراضي أو نطلب تحديد القسم
    # هنا نستخدم قسم "غير مصنف" مؤقتًا
    cat_id = ensure_uncategorized_category()
    success, author_id = db.add_author(author_name, cat_id)
    if not success:
        authors = db.get_authors_by_category(cat_id)
        author_id = next((a[0] for a in authors if a[1].lower() == author_name.lower()), None)

    context.user_data["author_id"] = author_id

    await update.message.reply_text(
        "📎 *أرسل ملف الكتاب (PDF أو أي ملف):*",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_BOOK_FILE


async def admin_add_book_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ يرجى إرسال ملف.")
        return WAITING_BOOK_FILE

    file_id = document.file_id
    title = context.user_data["book_title"]
    author_id = context.user_data["author_id"]

    db.add_book(title, author_id, file_id=file_id, added_by=ADMIN_ID)

    await update.message.reply_text("✅ تمت إضافة الكتاب بنجاح.")
    await admin_command(update, context)
    return ConversationHandler.END


# (يمكنك إضافة دوال تعديل وحذف الكتب بنفس النمط لاحقًا)


# ---------- إدارة المستخدمين ----------
async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    await query.edit_message_text(
        "👥 *إدارة المستخدمين*",
        reply_markup=admin_users_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    await query.edit_message_text(
        "🚫 *أرسل معرف المستخدم (ID) للحظر:*\n\nيمكنك معرفة الـ ID من خلال إعادة توجيه رسالة من المستخدم إلى @userinfobot.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_BAN_USER_ID


async def admin_ban_user_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text.strip())
        db.ban_user(user_id)
        await update.message.reply_text(f"✅ تم حظر المستخدم {user_id}.")
    except ValueError:
        await update.message.reply_text("❌ معرف غير صحيح.")

    await admin_command(update, context)
    return ConversationHandler.END


async def admin_unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    await query.edit_message_text(
        "✅ *أرسل معرف المستخدم (ID) لفك الحظر:*",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_UNBAN_USER_ID


async def admin_unban_user_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text.strip())
        db.unban_user(user_id)
        await update.message.reply_text(f"✅ تم فك حظر المستخدم {user_id}.")
    except ValueError:
        await update.message.reply_text("❌ معرف غير صحيح.")

    await admin_command(update, context)
    return ConversationHandler.END


async def admin_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    total_users = db.count_users()
    active_today = db.count_active_today()
    banned_count = db.count_banned_users()  # تحتاج إضافتها لـ database

    text = (
        f"👥 *إحصائيات المستخدمين:*\n\n"
        f"• إجمالي المستخدمين: {total_users}\n"
        f"• نشط اليوم: {active_today}\n"
        f"• محظور: {banned_count}"
    )
    await query.edit_message_text(text, reply_markup=admin_users_keyboard(), parse_mode=ParseMode.MARKDOWN)


# ---------- الإذاعة ----------
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    await query.edit_message_text(
        "📣 *أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:*\n\n"
        "يمكنك استخدام HTML أو Markdown.\nأرسل /cancel للإلغاء.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_BROADCAST_MESSAGE


async def admin_broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text_html if update.message.text else update.message.caption_html
    if not message_text:
        await update.message.reply_text("❌ أرسل نصاً.")
        return WAITING_BROADCAST_MESSAGE

    await update.message.reply_text("⏳ جاري الإرسال...")
    success, failed = await broadcast_message(context.bot, message_text, parse_mode="HTML")

    await update.message.reply_text(
        f"✅ تم الإرسال بنجاح إلى {success} مستخدم.\n❌ فشل مع {failed} مستخدم."
    )
    await admin_command(update, context)
    return ConversationHandler.END


# ---------- إدارة القنوات الإجبارية ----------
async def admin_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    channels = db.get_required_channels()
    await query.edit_message_text(
        "📢 *القنوات الإجبارية الحالية*",
        reply_markup=admin_channels_keyboard(channels),
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    await query.edit_message_text(
        "➕ *أرسل معرف القناة:*\n\nمثال: @channelusername أو -100123456789",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_CHANNEL_USERNAME


async def admin_add_channel_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    channel = update.message.text.strip()
    # تحقق سريع من أن البوت موجود في القناة (اختياري)
    try:
        # محاولة جلب معلومات القناة للتأكد
        chat = await context.bot.get_chat(channel)
        db.add_required_channel(channel)
        await update.message.reply_text(f"✅ تمت إضافة القناة {channel}.")
    except Exception as e:
        await update.message.reply_text(f"❌ تعذر التحقق من القناة. تأكد أن البوت مضاف كمسؤول.\nخطأ: {e}")

    await admin_command(update, context)
    return ConversationHandler.END


async def admin_delete_channel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END

    channel = query.data.split("_", 2)[2]  # adm_delch_@channel
    context.user_data["del_channel"] = channel
    await query.edit_message_text(
        f"⚠️ هل تريد حذف القناة {channel} من الإجبارية؟",
        reply_markup=confirm_cancel_keyboard("delch"),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_CHANNEL_DELETE_CONFIRM


async def admin_delete_channel_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data.startswith("confirm_"):
        channel = context.user_data.get("del_channel")
        db.remove_required_channel(channel)
        await query.edit_message_text(f"✅ تم حذف القناة {channel}.", reply_markup=admin_panel_keyboard())
    else:
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


# ---------- الإحصائيات المتقدمة ----------
async def admin_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    await query.edit_message_text(
        "📊 *الإحصائيات المتقدمة*",
        reply_markup=admin_stats_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_top_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    top_books = db.get_top_books(10)
    if not top_books:
        text = "لا توجد تحميلات بعد."
    else:
        lines = [f"{i+1}. *{title}* ({author}) - {count} تحميل" for i, (bid, title, count, author) in enumerate(top_books)]
        text = "📈 *أكثر الكتب تحميلاً:*\n\n" + "\n".join(lines)

    await query.edit_message_text(text, reply_markup=admin_stats_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def admin_top_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return

    top_cats = db.get_top_categories(5)
    lines = [f"{i+1}. *{name}* - {count} تحميل" for i, (cid, name, count) in enumerate(top_cats)]
    text = "📊 *أكثر الأقسام زيارة:*\n\n" + "\n".join(lines)

    await query.edit_message_text(text, reply_markup=admin_stats_keyboard(), parse_mode=ParseMode.MARKDOWN)


# ---------- دوال عامة للإلغاء ----------
async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu())
    return ConversationHandler.END


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


# ---------- تجميع الـ Handlers ----------
admin_handler = CommandHandler("admin", admin_command)

admin_callback_handlers = [
    CallbackQueryHandler(admin_back, pattern="^admin_back$"),
    CallbackQueryHandler(admin_categories_menu, pattern="^admin_categories$"),
    CallbackQueryHandler(admin_category_actions, pattern=r"^adm_cat_\d+$"),
    CallbackQueryHandler(admin_books_menu, pattern="^admin_books$"),
    CallbackQueryHandler(admin_users_menu, pattern="^admin_users$"),
    CallbackQueryHandler(admin_user_stats, pattern="^admin_user_stats$"),
    CallbackQueryHandler(admin_stats_menu, pattern="^admin_stats$"),
    CallbackQueryHandler(admin_top_books, pattern="^admin_top_books$"),
    CallbackQueryHandler(admin_top_categories, pattern="^admin_top_categories$"),
    CallbackQueryHandler(admin_channels_menu, pattern="^admin_channels$"),
]
# محادثة إدارة الأقسام
admin_category_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_add_category_start, pattern="^admin_add_category$"),
        CallbackQueryHandler(admin_edit_category_start, pattern=r"^adm_editcat_\d+$"),
        CallbackQueryHandler(admin_delete_category_confirm, pattern=r"^adm_delcat_\d+$"),
    ],
    states={
        WAITING_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_category_receive)],
        WAITING_CATEGORY_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_category_receive)],
        WAITING_CATEGORY_DELETE_CONFIRM: [CallbackQueryHandler(admin_delete_category_execute, pattern="^(confirm_|cancel_)")],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)

# محادثة إضافة كتاب يدوي
admin_book_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_add_book_manual_start, pattern="^admin_add_book_manual$")],
    states={
        WAITING_BOOK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_book_title_receive)],
        WAITING_BOOK_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_book_author_receive)],
        WAITING_BOOK_FILE: [MessageHandler(filters.Document.ALL, admin_add_book_file_receive)],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)
# محادثة حظر/فك حظر المستخدمين
admin_user_ban_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_ban_user_start, pattern="^admin_ban_user$"),
        CallbackQueryHandler(admin_unban_user_start, pattern="^admin_unban_user$"),
    ],
    states={
        WAITING_BAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_user_receive)],
        WAITING_UNBAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_unban_user_receive)],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)

# محادثة الإذاعة
admin_broadcast_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern="^admin_broadcast$")],
    states={
        WAITING_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_receive)],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)

# محادثة القنوات الإجبارية
admin_channel_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_add_channel_start, pattern="^admin_add_channel$"),
        CallbackQueryHandler(admin_delete_channel_confirm, pattern=r"^adm_delch_.+$"),
    ],
    states={
        WAITING_CHANNEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_receive)],
        WAITING_CHANNEL_DELETE_CONFIRM: [CallbackQueryHandler(admin_delete_channel_execute, pattern="^(confirm_|cancel_)")],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)
# ---------- بحث خارجي وإضافة كتاب للمالك ----------

async def admin_search_add_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await admin_only(update): return ConversationHandler.END
    await query.edit_message_text(
        "🔍 *أرسل اسم الكتاب + المؤلف للبحث عنه:*\n\n"
        "سيتم البحث في المصادر الخارجية وعرض النتائج لاختيار ما تريد إضافته.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_SEARCH_ADD_BOOK

async def admin_search_add_book_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text.strip()
    await update.message.reply_text("🔎 *جاري البحث في المصادر الخارجية...*", parse_mode=ParseMode.MARKDOWN)
    results = await search_external_books(query_text, limit=5)
    if not results:
        await update.message.reply_text("❌ لم يتم العثور على نتائج.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END
    context.user_data["search_results"] = results
    context.user_data["result_index"] = 0
    title, author, link = results[0]
    keyboard = [
        [InlineKeyboardButton("➕ إضافة هذا الكتاب", callback_data="add_search_result")],
        [InlineKeyboardButton("➡️ التالي", callback_data="next_search_result")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")],
    ]
    await update.message.reply_text(
        f"📖 *{title}*\n✍️ {author}\n🔗 {link}\n\nالنتيجة 1 من {len(results)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_SEARCH_ADD_BOOK

async def admin_search_result_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    results = context.user_data.get("search_results", [])
    index = context.user_data.get("result_index", 0)
    if query.data == "next_search_result":
        index = (index + 1) % len(results)
        context.user_data["result_index"] = index
        title, author, link = results[index]
        keyboard = [
            [InlineKeyboardButton("➕ إضافة هذا الكتاب", callback_data="add_search_result")],
            [InlineKeyboardButton("➡️ التالي", callback_data="next_search_result")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")],
        ]
        await query.edit_message_text(
            f"📖 *{title}*\n✍️ {author}\n🔗 {link}\n\nالنتيجة {index + 1} من {len(results)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == "add_search_result":
        title, author, link = results[index]
        cat_id = ensure_uncategorized_category()
        success, author_id = db.add_author(author, cat_id)
        if not success:
            authors = db.get_authors_by_category(cat_id)
            author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)
        if author_id:
            db.add_book(title, author_id, file_link=link, added_by=ADMIN_ID)
        await query.edit_message_text("✅ تمت إضافة الكتاب بنجاح.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END
    return WAITING_SEARCH_ADD_BOOK
    # ... نهاية الدوال التي أضفتها ...

# ⬇️⬇️⬇️ أضف هذا الكود هنا ⬇️⬇️⬇️
# محادثة بحث خارجي وإضافة كتاب
admin_search_add_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_search_add_book_start, pattern="^admin_search_add_book$")],
    states={
        WAITING_SEARCH_ADD_BOOK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_add_book_receive),
            CallbackQueryHandler(admin_search_result_navigation, pattern="^(next_search_result|add_search_result)$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel_action, pattern="^cancel_action$"), CommandHandler("cancel", cancel_action)],
)
# تجميع جميع المحادثات في قائمة واحدة لسهولة التسجيل
admin_conversation_handlers = [
    admin_category_conv,
    admin_book_conv,
    admin_user_ban_conv,
    admin_broadcast_conv,
    admin_channel_conv,
    admin_search_add_conv,
]
