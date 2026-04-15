# handlers/browse.py

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards import (
    categories_keyboard,
    authors_keyboard,
    books_keyboard,
    book_detail_keyboard,
    main_menu,
    subscription_required_keyboard,
)
from utils import check_user_subscription, get_required_channels_from_db

# عدد العناصر في الصفحة الواحدة
ITEMS_PER_PAGE = 5

# ---------- دوال مساعدة للتحقق من الاشتراك ----------
async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    يتحقق من اشتراك المستخدم في القنوات الإجبارية.
    إذا لم يكن مشتركاً، يعدل الرسالة لعرض قنوات الاشتراك ويعيد False.
    """
    user_id = update.effective_user.id
    is_subscribed, not_joined = await check_user_subscription(context.bot, user_id)
    
    if not is_subscribed:
        channels = await get_required_channels_from_db()
        keyboard = subscription_required_keyboard(channels)
        # إذا كانت الرسالة من CallbackQuery، نعدل الرسالة الحالية
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "⚠️ *يجب الاشتراك في القنوات التالية أولاً*",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "⚠️ *يجب الاشتراك في القنوات التالية أولاً*",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        return False
    return True

# ---------- عرض الأقسام ----------
async def browse_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة الأقسام (الصفحة الأولى)"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    # تسجيل النشاط
    db.update_activity(update.effective_user.id)
    
    categories = db.get_all_categories()
    if not categories:
        await query.edit_message_text(
            "❌ لا توجد أقسام حالياً. يرجى التواصل مع المالك.",
            reply_markup=main_menu()
        )
        return
    
    keyboard = categories_keyboard(categories, page=0, items_per_page=ITEMS_PER_PAGE)
    await query.edit_message_text(
        "📚 *الأقسام المتاحة:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def browse_categories_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التنقل بين صفحات الأقسام"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    # استخراج رقم الصفحة من callback_data (مثل catpage_2)
    page = int(query.data.split("_")[1])
    
    categories = db.get_all_categories()
    keyboard = categories_keyboard(categories, page=page, items_per_page=ITEMS_PER_PAGE)
    await query.edit_message_text(
        "📚 *الأقسام المتاحة:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ---------- عرض مؤلفي قسم معين ----------
async def browse_authors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة مؤلفي قسم محدد (الصفحة الأولى)"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    db.update_activity(update.effective_user.id)
    
    # استخراج معرف القسم من callback_data (مثل cat_5)
    category_id = int(query.data.split("_")[1])
    context.user_data["current_category"] = category_id
    
    authors = db.get_authors_by_category(category_id)
    category = db.get_category_by_id(category_id)
    cat_name = category[1] if category else "غير معروف"
    
    if not authors:
        await query.edit_message_text(
            f"❌ لا يوجد مؤلفون في قسم *{cat_name}* بعد.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    keyboard = authors_keyboard(authors, category_id, page=0, items_per_page=ITEMS_PER_PAGE)
    await query.edit_message_text(
        f"✍️ *مؤلفو قسم {cat_name}:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def browse_authors_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التنقل بين صفحات المؤلفين لقسم معين"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    # callback_data مثال: authpage_5_2 (القسم 5، صفحة 2)
    parts = query.data.split("_")
    category_id = int(parts[1])
    page = int(parts[2])
    
    authors = db.get_authors_by_category(category_id)
    category = db.get_category_by_id(category_id)
    cat_name = category[1] if category else "غير معروف"
    
    keyboard = authors_keyboard(authors, category_id, page=page, items_per_page=ITEMS_PER_PAGE)
    await query.edit_message_text(
        f"✍️ *مؤلفو قسم {cat_name}:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ---------- عرض كتب مؤلف معين ----------
async def browse_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض كتب مؤلف محدد"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    db.update_activity(update.effective_user.id)
    
    # استخراج معرف المؤلف من callback_data (مثل author_12)
    author_id = int(query.data.split("_")[1])
    context.user_data["current_author"] = author_id
    
    books = db.get_books_by_author(author_id)
    author = db.get_author_by_id(author_id)
    author_name = author[1] if author else "غير معروف"
    
    if not books:
        await query.edit_message_text(
            f"❌ لا توجد كتب للمؤلف *{author_name}* حالياً.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    keyboard = books_keyboard(books, author_id)
    await query.edit_message_text(
        f"📖 *كتب {author_name}:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ---------- العودة إلى مؤلفي قسم معين ----------
async def back_to_authors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عند الضغط على 'العودة للمؤلفين' من قائمة الكتب"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    # callback_data مثال: back_authors_12 (معرف المؤلف)
    author_id = int(query.data.split("_")[2])
    author = db.get_author_by_id(author_id)
    if not author:
        await browse_categories(update, context)
        return
    
    category_id = author[2]
    authors = db.get_authors_by_category(category_id)
    category = db.get_category_by_id(category_id)
    cat_name = category[1] if category else "غير معروف"
    
    keyboard = authors_keyboard(authors, category_id, page=0, items_per_page=ITEMS_PER_PAGE)
    await query.edit_message_text(
        f"✍️ *مؤلفو قسم {cat_name}:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ---------- تفاصيل كتاب وتحميل ----------
async def book_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تفاصيل كتاب معين مع أزرار التحميل"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    db.update_activity(update.effective_user.id)
    
    book_id = int(query.data.split("_")[1])
    book = db.get_book_by_id(book_id)
    
    if not book:
        await query.answer("الكتاب غير موجود", show_alert=True)
        return
    
    # book: (id, title, file_id, file_link, download_count, author_name, category_name)
    book_id, title, file_id, file_link, downloads, author_name, category_name = book
    
    message_text = (
        f"📘 *{title}*\n"
        f"✍️ المؤلف: {author_name}\n"
        f"📁 القسم: {category_name}\n"
        f"⬇️ عدد التحميلات: {downloads}\n"
    )
    
    keyboard = book_detail_keyboard(book_id, file_id, file_link)
    await query.edit_message_text(
        message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def download_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال ملف الكتاب للمستخدم وزيادة عداد التحميل"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    book_id = int(query.data.split("_")[1])
    book = db.get_book_by_id(book_id)
    
    if not book or not book[2]:  # book[2] هو file_id
        await query.answer("الملف غير متوفر حالياً", show_alert=True)
        return
    
    file_id = book[2]
    try:
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=file_id
        )
        db.increment_download(book_id)
        await query.answer("تم إرسال الكتاب ✅", show_alert=False)
    except Exception as e:
        await query.answer(f"حدث خطأ: {e}", show_alert=True)

# ---------- العودة إلى كتب مؤلف معين ----------
async def back_to_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عند الضغط على 'العودة للكتب' من صفحة تفاصيل الكتاب"""
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    book_id = int(query.data.split("_")[2])
    book = db.get_book_by_id(book_id)
    if not book:
        await browse_categories(update, context)
        return
    
    author_id = db.get_author_id_by_book(book_id)  # تحتاج دالة مساعدة في database
    if not author_id:
        await browse_categories(update, context)
        return
    
    books = db.get_books_by_author(author_id)
    author = db.get_author_by_id(author_id)
    author_name = author[1] if author else "غير معروف"
    
    keyboard = books_keyboard(books, author_id)
    await query.edit_message_text(
        f"📖 *كتب {author_name}:*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ---------- إنشاء الـ Handlers ----------
browse_handler = CallbackQueryHandler(browse_categories, pattern="^browse_categories$")

# تجميع كل الـ handlers المتعلقة بالتصفح
browse_handlers = [
    browse_handler,
    CallbackQueryHandler(browse_categories_page, pattern=r"^catpage_\d+$"),
    CallbackQueryHandler(browse_authors, pattern=r"^cat_\d+$"),
    CallbackQueryHandler(browse_authors_page, pattern=r"^authpage_\d+_\d+$"),
    CallbackQueryHandler(browse_books, pattern=r"^author_\d+$"),
    CallbackQueryHandler(back_to_authors, pattern=r"^back_authors_\d+$"),
    CallbackQueryHandler(book_detail, pattern=r"^book_\d+$"),
    CallbackQueryHandler(download_book, pattern=r"^download_\d+$"),
    CallbackQueryHandler(back_to_books, pattern=r"^back_books_\d+$"),
      ]
