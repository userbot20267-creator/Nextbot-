# handlers/search.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# البحث المحسن الذي يدعم Internet Archive والغلاف
from services.scraper import search_external_books_enhanced as search_external_books
from services.scraper import download_file_from_url

# حالة المحادثة للبحث
WAITING_SEARCH_QUERY = 1


# ---------- دوال مساعدة ----------
def ensure_uncategorized_category() -> int:
    """يتأكد من وجود قسم 'غير مصنف' ويعيد معرفه، ينشئه إذا لم يوجد"""
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


def get_search_example() -> str:
    """ترجع أمثلة على صيغ البحث الصحيحة"""
    return (
        "🔍 *أمثلة على صيغ البحث:*\n"
        "• `الخيميائي باولو كويلو`\n"
        "• `Clean Code Robert Martin`\n\n"
        "يمكنك كتابة اسم الكتاب والمؤلف معًا."
    )


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
        "🔍 *أرسل اسم الكتاب + اسم المؤلف (بالعربية أو الإنجليزية):*\n\n"
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

    db.update_activity(user_id)

    # 1. البحث في قاعدة البيانات المحلية
    local_results = db.search_books(query_text)

    # 2. البحث الخارجي (Internet Archive + Open Library + Google Books)
    external_results = []
    if not local_results:
        await update.message.reply_text(
            "🔎 *لم يتم العثور على نتائج محلية. جاري البحث في المصادر الخارجية...*",
            parse_mode=ParseMode.MARKDOWN
        )
        external_results = await search_external_books(query_text)

        # ⬇️⬇️⬇️ تم تعطيل الأرشفة التلقائية بالكامل ⬇️⬇️⬇️
        # (سيتم التعامل مع الكتب الخارجية عبر نظام طلب الموافقة لاحقًا)
        # for item in external_results:
        #     title, author, link, cover_url = item
        #     cat_id = ensure_uncategorized_category()
        #     success, author_id = db.add_author(author, cat_id)
        #     if not success:
        #         authors = db.get_authors_by_category(cat_id)
        #         author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)
        #     if author_id:
        #         db.add_book(title, author_id, file_link=link, added_by=user_id)
        # ⬆️⬆️⬆️ نهاية التعطيل ⬆️⬆️⬆️

    # 3. عرض النتائج
    if not local_results and not external_results:
        await update.message.reply_text(
            f"❌ *لم يتم العثور على أي نتائج.*\n\n{get_search_example()}",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    # عرض النتائج المحلية (كتب موجودة بالفعل في البوت)
    for book in local_results:
        book_id, title, file_id, file_link, downloads, author_name, category_name = book
        if file_id:
            try:
                await update.message.reply_document(
                    document=file_id,
                    caption=f"📖 *{title}*\n✍️ {author_name}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ في إرسال الملف: {e}")

    # عرض النتائج الخارجية: محاولة تحميل وإرسال الملف، وإلا رابط
    for ext in external_results:
        title, author, link, cover_url = ext
        status_msg = await update.message.reply_text(
            f"⏳ *جاري تجهيز:* {title}",
            parse_mode=ParseMode.MARKDOWN
        )

        tmp_path = await download_file_from_url(link)
        file_sent = False
        if tmp_path:
            try:
                with open(tmp_path, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        caption=f"📖 *{title}*\n✍️ {author}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                os.unlink(tmp_path)
                file_sent = True
                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"❌ فشل إرسال الملف. جارٍ إرسال الرابط...")

        if not file_sent:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 رابط الكتاب", url=link)]
            ])
            await status_msg.edit_text(
                f"📖 *{title}*\n✍️ {author}\n\n⚠️ تعذر التحميل التلقائي. استخدم الزر أدناه.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )

    await update.message.reply_text(
        "✅ *تم عرض النتائج.*",
        reply_markup=main_menu(),
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

search_callback_handlers = [
    CallbackQueryHandler(new_search_prompt, pattern="^search_prompt$"),
]
