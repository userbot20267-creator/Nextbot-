# handlers/search.py

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CommandHandler
)
from telegram.constants import ParseMode

import database as db
from keyboards import (
    search_prompt_keyboard,
    search_results_keyboard,
    main_menu,
    cancel_only_keyboard,
    subscription_required_keyboard
)
from utils import check_user_subscription, get_required_channels_from_db
from utils.scraping import search_external_books

# حالة المحادثة للبحث
WAITING_SEARCH_QUERY = 1


# ---------- دوال مساعدة ----------
def ensure_uncategorized_category() -> int:
    """يتأكد من وجود قسم 'غير مصنف' ويعيد معرفه، ينشئه إذا لم يوجد"""
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    # إنشاء القسم
    db.add_category("غير مصنف")
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    return 1  # fallback


# ---------- بدء عملية البحث ----------
async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يطلب من المستخدم إدخال اسم الكتاب + المؤلف"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    is_subscribed, _ = await check_user_subscription(context.bot, user_id)
    if not is_subscribed:
        channels = await get_required_channels_from_db()
        await query.edit_message_text(
            "⚠️ *يجب الاشتراك في القنوات أولاً*",
            reply_markup=subscription_required_keyboard(channels),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "🔍 *أرسل اسم الكتاب + اسم المؤلف:*\n\n"
        "مثال: `الخيميائي باولو كويلو`\n\n"
        "أو أرسل /cancel للإلغاء.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_SEARCH_QUERY


# ---------- استقبال نص البحث وتنفيذه ----------
async def receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال نص البحث والقيام بالبحث الداخلي والخارجي"""
    user_id = update.effective_user.id
    query_text = update.message.text.strip()

    # تسجيل النشاط
    db.update_activity(user_id)

    # 1. البحث في قاعدة البيانات المحلية
    local_results = db.search_books(query_text)

    # 2. البحث الخارجي (Open Library + Google Books إن وجد)
    external_results = []
    if not local_results:
        await update.message.reply_text(
            "🔎 *لم يتم العثور على نتائج محلية. جاري البحث في المصادر الخارجية...*",
            parse_mode=ParseMode.MARKDOWN
        )
        external_results = await search_external_books(query_text)

        # الأرشفة التلقائية: حفظ النتائج الخارجية في قاعدة البيانات
        for title, author, link in external_results:
            # التأكد من وجود قسم "غير مصنف"
            cat_id = ensure_uncategorized_category()

            # محاولة إضافة المؤلف أو استرجاع معرفه إذا كان موجوداً
            success, author_id = db.add_author(author, cat_id)
            if not success:
                # المؤلف موجود مسبقاً، نجلب معرفه
                authors = db.get_authors_by_category(cat_id)
                author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)

            # إضافة الكتاب مع الرابط الخارجي
            if author_id:
                db.add_book(
                    title=title,
                    author_id=author_id,
                    file_link=link,
                    added_by=user_id
                )

    # 3. عرض النتائج
    if not local_results and not external_results:
        await update.message.reply_text(
            "❌ *لم يتم العثور على أي نتائج.*\n"
            "حاول بصيغة أخرى أو تأكد من الإملاء.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    # تجهيز قائمة النتائج للعرض
    combined_results = []

    # إضافة النتائج المحلية
    for book in local_results:
        # book: (id, title, file_id, file_link, downloads, author_name, category_name)
        combined_results.append(book)

    # إضافة النتائج الخارجية (قد تكون أقل تفصيلاً)
    for ext in external_results:
        combined_results.append(ext)

    keyboard = search_results_keyboard(combined_results)
    await update.message.reply_text(
        f"✅ *تم العثور على {len(combined_results)} نتيجة:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ---------- إلغاء البحث ----------
async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء عملية البحث والعودة للقائمة الرئيسية"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "❌ تم إلغاء البحث.",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ تم إلغاء البحث.",
            reply_markup=main_menu()
        )
    return ConversationHandler.END


# ---------- معالجة طلب بحث جديد من نتائج سابقة ----------
async def new_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """زر 'بحث جديد' داخل قائمة النتائج - يعيد بدء المحادثة"""
    query = update.callback_query
    await query.answer()
    # نعيد توجيه المستخدم إلى بداية المحادثة
    await search_prompt(update, context)


# ---------- Handlers ----------
search_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(search_prompt, pattern="^search_prompt$")
    ],
    states={
        WAITING_SEARCH_QUERY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_query)
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_search, pattern="^cancel_action$"),
        CommandHandler("cancel", cancel_search),
    ],
)

# معالجات منفصلة للأزرار داخل نتائج البحث
search_callback_handlers = [
    CallbackQueryHandler(new_search_prompt, pattern="^search_prompt$"),
  ]
