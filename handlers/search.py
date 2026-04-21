# handlers/search.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from services.scraper import download_file_to_telegram
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

from services.scraper import search_external_books_enhanced as search_external_books
from services.scraper import download_file_from_url

# حالات المحادثة
WAITING_SEARCH_QUERY = 1
WAITING_BOOK_SELECTION = 2  # حالة جديدة لانتظار اختيار المستخدم

# عدد النتائج لكل صفحة
RESULTS_PER_PAGE = 5


# ---------- دوال مساعدة ----------
def ensure_uncategorized_category() -> int:
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
    return (
        "🔍 *أمثلة على صيغ البحث:*\n"
        "• `الخيميائي باولو كويلو`\n"
        "• `Clean Code Robert Martin`\n\n"
        "يمكنك كتابة اسم الكتاب والمؤلف معًا."
    )


async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


async def receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال نص البحث وعرض النتائج كأزرار تفاعلية"""
    user_id = update.effective_user.id
    query_text = update.message.text.strip()

    db.update_activity(user_id)

    # حفظ كلمة البحث في الجلسة
    context.user_data['last_search_query'] = query_text
    context.user_data['search_page'] = 0
    context.user_data['search_results'] = None  # سيتم تخزين النتائج هنا

    # 1. البحث في قاعدة البيانات المحلية
    local_results = db.search_books(query_text)

    # 2. البحث الخارجي
    external_results = []
    if not local_results:
        status_msg = await update.message.reply_text(
            "🔎 *لم يتم العثور على نتائج محلية. جاري البحث في المصادر الخارجية...*",
            parse_mode=ParseMode.MARKDOWN
        )
        external_results = await search_external_books(query_text)
        await status_msg.delete()

    # دمج النتائج (محلية أولاً ثم خارجية)
    all_results = []
    
    # تنسيق النتائج المحلية
    for book in local_results:
        book_id, title, file_id, file_link, downloads, author_name, category_name = book
        all_results.append({
            'type': 'local',
            'id': book_id,
            'title': title,
            'author': author_name,
            'category': category_name,
            'file_id': file_id,
            'file_link': file_link,
            'downloads': downloads
        })
    
    # تنسيق النتائج الخارجية
    for ext in external_results:
        title, author, link, cover_url = ext
        all_results.append({
            'type': 'external',
            'title': title,
            'author': author,
            'link': link,
            'cover_url': cover_url
        })

    if not all_results:
        await update.message.reply_text(
            f"❌ *لم يتم العثور على أي نتائج.*\n\n{get_search_example()}",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    # حفظ النتائج في الجلسة
    context.user_data['search_results'] = all_results
    
    # عرض النتائج الأولى
    await show_search_results_page(update, context, page=0)
    return WAITING_BOOK_SELECTION


async def show_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """عرض صفحة من نتائج البحث كأزرار تفاعلية"""
    results = context.user_data.get('search_results', [])
    query_text = context.user_data.get('last_search_query', '')
    
    if not results:
        await update.message.reply_text("❌ لا توجد نتائج للعرض.")
        return
    
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)
    page_results = results[start_idx:end_idx]
    
    # بناء لوحة المفاتيح
    keyboard = []
    
    for idx, book in enumerate(page_results, start=start_idx + 1):
        # اختصار العنوان الطويل
        display_title = book['title'][:35] + "..." if len(book['title']) > 35 else book['title']
        display_author = book['author'][:20] + "..." if len(book['author']) > 20 else book['author']
        
        button_text = f"{idx}. 📖 {display_title} - {display_author}"
        
        # تخزين مؤقت للكتاب المختار
        callback_data = f"select_book_{book['type']}_{start_idx + (idx - start_idx - 1)}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"search_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"search_page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # أزرار إضافية
    keyboard.append([InlineKeyboardButton("🔄 بحث جديد", callback_data="new_search"), InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_action")])
    
    # نص الرسالة
    text = f"🔍 *نتائج البحث عن:* \"{query_text}\"\n"
    text += f"📊 *عدد النتائج:* {total_results} | 📄 *الصفحة:* {page + 1}/{total_pages}\n\n"
    text += "👇 *اختر الكتاب المناسب:*"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    context.user_data['search_page'] = page


async def search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التنقل بين صفحات النتائج"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    await show_search_results_page(update, context, page)


async def select_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند اختيار كتاب من القائمة، عرض تفاصيله وأزرار التحميل"""
    query = update.callback_query
    await query.answer()
    
    # استخراج نوع الكتاب ومؤشره
    parts = query.data.split("_")
    book_type = parts[2]  # 'local' or 'external'
    book_index = int(parts[3])
    
    results = context.user_data.get('search_results', [])
    if book_index >= len(results):
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return
    
    selected_book = results[book_index]
    
    # بناء نص التفاصيل
    text = f"📖 *{selected_book['title']}*\n\n"
    text += f"✍️ *المؤلف:* {selected_book['author']}\n"
    
    if 'category' in selected_book and selected_book['category']:
        text += f"📂 *القسم:* {selected_book['category']}\n"
    
    if 'downloads' in selected_book:
        text += f"📥 *مرات التحميل:* {selected_book['downloads']}\n"
    
    text += "\n👇 *ماذا تريد أن تفعل؟*"
    
    # بناء أزرار التفاعل
    keyboard = []
    
    if book_type == 'local':
        # كتاب موجود محلياً
        if selected_book.get('file_id'):
            keyboard.append([InlineKeyboardButton("📥 تحميل الكتاب", callback_data=f"download_local_{selected_book['id']}")])
    else:
        # كتاب خارجي - نعرض خيار التنزيل
        keyboard.append([InlineKeyboardButton("📥 تنزيل الكتاب", callback_data=f"download_external_{book_index}")])
    
    keyboard.append([InlineKeyboardButton("🔍 بحث جديد", callback_data="new_search")])
    keyboard.append([InlineKeyboardButton("🔙 العودة للنتائج", callback_data=f"back_to_results")])
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


async def download_local_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحميل كتاب محلي موجود مسبقاً"""
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    
    # جلب الكتاب من قاعدة البيانات
    book = db.get_book_by_id(book_id)
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return
    
    # تحديث عداد التحميلات
    db.increment_downloads(book_id)
    
    book_id, title, file_id, file_link, downloads, author_name, category_name = book
    
    if file_id:
        try:
            await query.message.reply_document(
                document=file_id,
                caption=f"📖 *{title}*\n✍️ {author_name}\n📥 تم التحميل {downloads + 1} مرة",
                parse_mode=ParseMode.MARKDOWN
            )
            await query.edit_message_text(f"✅ تم إرسال كتاب *{title}*", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(f"❌ خطأ في إرسال الملف: {e}")
    elif file_link:
        await query.edit_message_text(f"📥 رابط التحميل: {file_link}")
    else:
        await query.edit_message_text("❌ لا يوجد رابط أو ملف لهذا الكتاب.")


async def download_external_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنزيل كتاب من مصدر خارجي وعرضه للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    book_index = int(query.data.split("_")[-1])
    results = context.user_data.get('search_results', [])
    
    if book_index >= len(results):
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return
    
    book = results[book_index]
    
    status_msg = await query.edit_message_text(
        f"⏳ *جاري تنزيل وتجهيز:* {book['title']}\nقد يستغرق هذا دقيقة.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # تنزيل ورفع الملف
    file_id = await download_file_to_telegram(context.bot, book['link'], update.effective_user.id)
    
    if file_id:
        try:
            await query.message.reply_document(
                document=file_id,
                caption=f"📖 *{book['title']}*\n✍️ {book['author']}\n\n✅ تم التنزيل بنجاح",
                parse_mode=ParseMode.MARKDOWN
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ فشل إرسال الملف: {e}")
    else:
        await status_msg.edit_text(
            f"❌ *تعذر تنزيل الكتاب:* {book['title']}\n"
            f"قد يكون الرابط غير صالح أو الملف كبيراً جداً.",
            parse_mode=ParseMode.MARKDOWN
        )


async def back_to_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى قائمة نتائج البحث"""
    query = update.callback_query
    await query.answer()
    
    page = context.user_data.get('search_page', 0)
    await show_search_results_page(update, context, page)


async def new_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """زر 'بحث جديد' - يعيد بدء المحادثة"""
    query = update.callback_query
    await query.answer()
    
    # مسح بيانات البحث القديمة
    context.user_data.pop('last_search_query', None)
    context.user_data.pop('search_results', None)
    context.user_data.pop('search_page', None)
    
    await search_prompt(update, context)


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء البحث والعودة للقائمة الرئيسية"""
    # مسح بيانات البحث
    context.user_data.pop('last_search_query', None)
    context.user_data.pop('search_results', None)
    context.user_data.pop('search_page', None)
    
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


# ---------- Handlers ----------
search_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(search_prompt, pattern="^search_prompt$")
    ],
    states={
        WAITING_SEARCH_QUERY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_search_query)
        ],
        WAITING_BOOK_SELECTION: [
            CallbackQueryHandler(search_page_callback, pattern="^search_page_"),
            CallbackQueryHandler(select_book_callback, pattern="^select_book_"),
            CallbackQueryHandler(download_local_book, pattern="^download_local_"),
            CallbackQueryHandler(download_external_book, pattern="^download_external_"),
            CallbackQueryHandler(back_to_results, pattern="^back_to_results$"),
            CallbackQueryHandler(new_search_prompt, pattern="^new_search$"),
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
