# handlers/ai_search.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
import database as db
from services.ai_service import ai_search_book, find_book_download_url
from services.scraper import download_file_to_telegram
from keyboards import cancel_only_keyboard
from config import ADMIN_ID

# حالات المحادثة
WAITING_AI_QUERY, WAITING_CATEGORY_SELECTION = range(2)

async def ai_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء محادثة البحث بالذكاء الاصطناعي (للمالك فقط)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🤖 *أهلاً بك في وضع البحث الذكي*\n\n"
        "أرسل لي وصفاً للكتاب الذي تريد إضافته (مثال: 'رواية الخيميائي لباولو كويلو'):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_only_keyboard()
    )
    return WAITING_AI_QUERY

async def receive_ai_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال استعلام المستخدم وتحليله"""
    query_text = update.message.text.strip()
    await update.message.reply_text("🧠 جارٍ تحليل طلبك بالذكاء الاصطناعي...")

    # 1. استخراج العنوان والمؤلف باستخدام AI
    book_info = await ai_search_book(query_text)
    if not book_info:
        await update.message.reply_text("❌ لم أتمكن من فهم الطلب. حاول مرة أخرى.")
        return WAITING_AI_QUERY

    title = book_info.get("title", "")
    author = book_info.get("author", "")

    await update.message.reply_text(
        f"📚 *تم التعرف على:*\nالعنوان: {title}\nالمؤلف: {author}\n\n"
        "🔍 جارٍ البحث عن رابط التحميل...",
        parse_mode=ParseMode.MARKDOWN
    )

    # 2. البحث عن رابط تحميل
    download_url = await find_book_download_url(title, author)
    if not download_url:
        await update.message.reply_text("❌ لم أتمكن من العثور على رابط تحميل لهذا الكتاب.")
        return ConversationHandler.END

    # حفظ المعلومات لاستخدامها لاحقاً
    context.user_data["ai_book_title"] = title
    context.user_data["ai_book_author"] = author
    context.user_data["ai_download_url"] = download_url

    # 3. عرض قائمة الأقسام للاختيار
    categories = db.get_all_categories()
    if not categories:
        await update.message.reply_text("❌ لا توجد أقسام. أضف قسماً أولاً.")
        return ConversationHandler.END

    keyboard = []
    for cat_id, cat_name in categories:
        keyboard.append([InlineKeyboardButton(cat_name, callback_data=f"ai_cat_{cat_id}")])
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")])

    await update.message.reply_text(
        "📁 *اختر القسم الذي تريد إضافة الكتاب إليه:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_CATEGORY_SELECTION

async def receive_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اختيار القسم، تنزيل الملف وإضافته"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_action":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

    cat_id = int(query.data.split("_")[-1])
    title = context.user_data["ai_book_title"]
    author_name = context.user_data["ai_book_author"]
    download_url = context.user_data["ai_download_url"]

    await query.edit_message_text("⏳ جارٍ تنزيل الملف من الإنترنت... قد يستغرق ذلك بعض الوقت.")

    # 1. تنزيل الملف ورفعه إلى تليجرام
    file_id = await download_file_to_telegram(context.bot, download_url, update.effective_user.id)
    if not file_id:
        await query.edit_message_text("❌ فشل تنزيل الملف. قد يكون الرابط غير صالح أو الملف كبيراً جداً.")
        return ConversationHandler.END

    # 2. التأكد من وجود المؤلف في القسم المختار (أو إنشاؤه)
    success, author_id = db.add_author(author_name, cat_id)
    if not success:
        # المؤلف موجود مسبقاً، نجلب معرفه
        authors = db.get_authors_by_category(cat_id)
        author_id = next((a[0] for a in authors if a[1].lower() == author_name.lower()), None)

    if not author_id:
        await query.edit_message_text("❌ حدث خطأ أثناء تجهيز المؤلف.")
        return ConversationHandler.END

    # 3. إضافة الكتاب إلى قاعدة البيانات
    db.add_book(title, author_id, file_id=file_id, added_by=ADMIN_ID)

    await query.edit_message_text(
        f"✅ *تمت إضافة الكتاب بنجاح!*\n"
        f"📖 {title}\n✍️ {author_name}\n📁 القسم: {cat_id}",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة"""
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ تم إلغاء العملية.")
    else:
        await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END

# بناء المحادثة
ai_search_conv = ConversationHandler(
    entry_points=[CommandHandler("ai_search", ai_search_start)],
    states={
        WAITING_AI_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ai_query)],
        WAITING_CATEGORY_SELECTION: [
            CallbackQueryHandler(receive_category_selection, pattern=r"^ai_cat_\d+$"),
            CallbackQueryHandler(cancel, pattern="^cancel_action$")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
  )
