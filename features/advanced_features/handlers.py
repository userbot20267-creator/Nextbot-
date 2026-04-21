# features/advanced_features/handlers.py
"""
ميزات متقدمة للبوت:
1. نظام طلب الكتب (/request)
2. اقتراح كتب بناءً على المزاج (/mood)
3. إضافة كتب تلقائية بواسطة الذكاء الاصطناعي للمالك (/ai_add_books)
"""

import os
import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
import database as db
from config import ADMIN_ID, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from keyboards import admin_panel_keyboard, main_menu, cancel_only_keyboard

# حالات المحادثة
WAITING_REQUEST_TITLE = 1
WAITING_REQUEST_AUTHOR = 2
WAITING_MOOD = 3
WAITING_AI_SEARCH_QUERY = 4
WAITING_AI_SEARCH_RESULTS = 5

# عدد الطلبات لكل صفحة
REQUESTS_PER_PAGE = 10


# ==================== نظام طلب الكتب ====================

async def request_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية طلب كتاب - طلب عنوان الكتاب"""
    user_id = update.effective_user.id
    db.update_activity(user_id)
    
    await update.message.reply_text(
        "📝 *نظام طلب الكتب*\n\n"
        "يمكنك طلب كتاب غير موجود في المكتبة.\n\n"
        "✏️ *أرسل عنوان الكتاب الذي تبحث عنه:*\n"
        "مثال: `الخيميائي`\n\n"
        "أو أرسل /cancel للإلغاء.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_only_keyboard()
    )
    return WAITING_REQUEST_TITLE


async def receive_request_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال عنوان الكتاب وطلب المؤلف"""
    title = update.message.text.strip()
    context.user_data['request_title'] = title
    
    await update.message.reply_text(
        f"📖 *عنوان الكتاب:* {title}\n\n"
        "✍️ *أرسل اسم المؤلف (اختياري):*\n"
        "يمكنك كتابة /skip للتخطي.\n\n"
        "أو أرسل /cancel للإلغاء.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_only_keyboard()
    )
    return WAITING_REQUEST_AUTHOR


async def receive_request_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال المؤلف وحفظ الطلب"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user = update.effective_user
    
    title = context.user_data.get('request_title', '')
    
    if text.lower() == '/skip':
        author = "غير محدد"
    else:
        author = text
    
    # حفظ الطلب في قاعدة البيانات
    success = db.add_book_request(
        user_id=user_id,
        user_name=user.full_name,
        user_username=user.username,
        title=title,
        author=author
    )
    
    if success:
        await update.message.reply_text(
            f"✅ *تم إرسال طلبك بنجاح!*\n\n"
            f"📖 *الكتاب:* {title}\n"
            f"✍️ *المؤلف:* {author}\n\n"
            f"سيتم مراجعة الطلب وإضافته قريباً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        
        # إشعار المالك (إذا كان متصلاً)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📢 *طلب كتاب جديد*\n\n"
                     f"👤 *المستخدم:* {user.full_name}\n"
                     f"🆔 *المعرف:* `{user_id}`\n"
                     f"📖 *الكتاب:* {title}\n"
                     f"✍️ *المؤلف:* {author}\n\n"
                     f"لعرض جميع الطلبات استخدم /view_requests",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء حفظ الطلب. حاول مرة أخرى لاحقاً.",
            reply_markup=main_menu()
        )
    
    context.user_data.pop('request_title', None)
    return ConversationHandler.END


# ==================== عرض طلبات الكتب للمالك ====================

async def view_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة طلبات الكتب (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return
    
    await show_requests_page(update, context, page=0)


async def show_requests_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """عرض صفحة من طلبات الكتب"""
    offset = page * REQUESTS_PER_PAGE
    requests = db.get_book_requests(limit=REQUESTS_PER_PAGE, offset=offset)
    total_requests = db.count_book_requests()
    total_pages = (total_requests + REQUESTS_PER_PAGE - 1) // REQUESTS_PER_PAGE if total_requests > 0 else 1
    
    if not requests:
        text = "📭 *لا توجد طلبات كتب حالياً.*"
        keyboard = [[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")]]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = f"📋 *طلبات الكتب (صفحة {page + 1} من {total_pages})*\n\n"
    
    keyboard = []
    for req in requests:
        req_id, user_id, user_name, user_username, title, author, status, created_at = req
        
        status_emoji = "⏳" if status == "pending" else "✅" if status == "approved" else "❌"
        text += f"{status_emoji} *{title}*\n"
        text += f"   👤 {user_name} | ✍️ {author}\n"
        text += f"   📅 {created_at.strftime('%Y-%m-%d')}\n\n"
        
        # أزرار لكل طلب
        keyboard.append([
            InlineKeyboardButton(f"📖 إضافة {title[:20]}", callback_data=f"approve_req_{req_id}"),
            InlineKeyboardButton("🗑 حذف", callback_data=f"delete_req_{req_id}")
        ])
    
    # أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"req_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"req_page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def requests_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التنقل بين صفحات الطلبات"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    await show_requests_page(update, context, page)


async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب كتاب وبدء عملية إضافته"""
    query = update.callback_query
    await query.answer()
    
    req_id = int(query.data.split("_")[-1])
    request_data = db.get_book_request(req_id)
    
    if not request_data:
        await query.edit_message_text("❌ الطلب غير موجود.")
        return
    
    req_id, user_id, user_name, user_username, title, author, status, created_at = request_data
    
    # تحديث حالة الطلب
    db.update_request_status(req_id, "approved")
    
    # تخزين بيانات الطلب للاستخدام لاحقاً
    context.user_data['approving_request'] = {
        'req_id': req_id,
        'title': title,
        'author': author,
        'user_id': user_id
    }
    
    # بدء عملية إضافة الكتاب
    keyboard = [
        [InlineKeyboardButton("➕ إضافة يدوياً", callback_data="add_manual_from_req")],
        [InlineKeyboardButton("🤖 بحث تلقائي", callback_data="ai_search_from_req")],
        [InlineKeyboardButton("🔙 العودة للطلبات", callback_data="back_to_requests")]
    ]
    
    await query.edit_message_text(
        f"✅ *تمت الموافقة على طلب:* {title}\n\n"
        f"كيف تريد إضافة الكتاب؟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delete_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف طلب كتاب"""
    query = update.callback_query
    await query.answer()
    
    req_id = int(query.data.split("_")[-1])
    db.update_request_status(req_id, "rejected")
    db.delete_book_request(req_id)
    
    await query.edit_message_text("✅ تم حذف الطلب.")
    
    # تحديث قائمة الطلبات
    await show_requests_page(update, context, page=0)


async def back_to_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى قائمة الطلبات"""
    query = update.callback_query
    await query.answer()
    await show_requests_page(update, context, page=0)


# ==================== اقتراح كتب بناءً على المزاج ====================

async def mood_suggestion_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء اقتراح كتب بناءً على المزاج"""
    user_id = update.effective_user.id
    db.update_activity(user_id)
    
    keyboard = [
        [InlineKeyboardButton("😊 سعيد", callback_data="mood_happy")],
        [InlineKeyboardButton("😢 حزين", callback_data="mood_sad")],
        [InlineKeyboardButton("😌 متوتر", callback_data="mood_stressed")],
        [InlineKeyboardButton("🤩 متحمس", callback_data="mood_excited")],
        [InlineKeyboardButton("😴 متعب", callback_data="mood_tired")],
        [InlineKeyboardButton("❤️ رومانسي", callback_data="mood_romantic")],
        [InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_action")]
    ]
    
    await update.message.reply_text(
        "🎭 *اقتراح كتب حسب المزاج*\n\n"
        "اختر ما تشعر به الآن، وسأقترح عليك كتاباً مناسباً من مكتبتنا:\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_MOOD


async def mood_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تم اختيار المزاج - استخدام AI لاقتراح كتاب"""
    query = update.callback_query
    await query.answer()
    
    mood = query.data.split("_")[-1]
    
    # ترجمة المزاج إلى نص عربي
    mood_map = {
        'happy': 'سعيد',
        'sad': 'حزين',
        'stressed': 'متوتر',
        'excited': 'متحمس',
        'tired': 'متعب',
        'romantic': 'رومانسي'
    }
    
    mood_text = mood_map.get(mood, mood)
    
    await query.edit_message_text(
        f"🎭 *أنت تشعر بـ: {mood_text}*\n\n"
        f"🤖 *جاري البحث عن كتاب مناسب...*\n"
        f"قد يستغرق هذا بضع ثوانٍ.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # البحث في قاعدة البيانات عن كتب
    all_books = db.get_all_books()
    
    if not all_books:
        await query.edit_message_text(
            "📭 *لا توجد كتب في المكتبة حالياً.*\n"
            "تواصل مع المالك لإضافة كتب.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return ConversationHandler.END
    
    # استخدام AI لاقتراح كتاب مناسب
    suggested_books = await ai_suggest_books_by_mood(mood_text, all_books)
    
    if not suggested_books:
        # إذا فشل AI، اقترح كتباً عشوائية
        import random
        suggested_books = random.sample(all_books, min(3, len(all_books)))
        suggested_books = [(book[1], book[5]) for book in suggested_books]  # title, author
    
    # عرض الاقتراحات
    text = f"🎭 *بناءً على شعورك بـ {mood_text}، أقترح عليك هذه الكتب:*\n\n"
    
    keyboard = []
    for title, author in suggested_books[:3]:
        text += f"📖 *{title}*\n✍️ {author}\n\n"
        
        # البحث عن معرف الكتاب
        book = db.get_book_by_title(title)
        if book:
            book_id = book[0]
            keyboard.append([InlineKeyboardButton(f"📖 عرض {title[:25]}", callback_data=f"view_book_{book_id}")])
    
    keyboard.append([InlineKeyboardButton("🎭 مزاج آخر", callback_data="mood_again"), InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def mood_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة اختيار المزاج"""
    query = update.callback_query
    await query.answer()
    await mood_suggestion_start(update, context)
    return WAITING_MOOD


# ==================== إضافة كتب تلقائية بواسطة AI للمالك ====================

async def ai_add_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /ai_add_books - إضافة كتب تلقائياً باستخدام AI (للمالك فقط)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID and not db.is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return
    
    await update.message.reply_text(
        "🤖 *إضافة كتب تلقائية بالذكاء الاصطناعي*\n\n"
        "أرسل عنوان الكتاب أو الموضوع الذي تريد البحث عنه:\n"
        "مثال: `كتب عن تطوير الذات`\n"
        "مثال: `روايات عربية حديثة`\n"
        "مثال: `كتب عن البرمجة`\n\n"
        "أو أرسل /cancel للإلغاء.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_only_keyboard()
    )
    return WAITING_AI_SEARCH_QUERY


async def receive_ai_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال استعلام البحث من المالك والبحث عن كتب"""
    query_text = update.message.text.strip()
    
    await update.message.reply_text(
        f"🔍 *جاري البحث عن كتب حول:* \"{query_text}\"\n"
        f"قد يستغرق هذا 30-60 ثانية...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # البحث عن كتب باستخدام AI
    books = await ai_search_books(query_text)
    
    if not books:
        await update.message.reply_text(
            "❌ *لم يتم العثور على كتب.*\n"
            "حاول بكلمات بحث مختلفة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # حفظ النتائج في الجلسة
    context.user_data['ai_search_results'] = books
    context.user_data['ai_search_page'] = 0
    
    await show_ai_search_results(update, context, page=0)
    return WAITING_AI_SEARCH_RESULTS


async def show_ai_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """عرض نتائج البحث عن الكتب"""
    results = context.user_data.get('ai_search_results', [])
    
    if not results:
        await update.message.reply_text("❌ لا توجد نتائج.")
        return
    
    total_results = len(results)
    total_pages = (total_results + 1) // 2  # كتابان لكل صفحة
    
    start_idx = page * 2
    end_idx = min(start_idx + 2, total_results)
    page_results = results[start_idx:end_idx]
    
    text = f"🤖 *نتائج البحث (الصفحة {page + 1} من {total_pages})*\n\n"
    
    keyboard = []
    for book in page_results:
        text += f"📖 *{book['title']}*\n"
        text += f"✍️ {book['author']}\n"
        if book.get('description'):
            desc = book['description'][:150] + "..." if len(book['description']) > 150 else book['description']
            text += f"📝 {desc}\n"
        text += "\n"
        
        # زر إضافة الكتاب
        keyboard.append([InlineKeyboardButton(f"➕ إضافة {book['title'][:30]}", callback_data=f"ai_add_book_{start_idx + page_results.index(book)}")])
    
    # أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"ai_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"ai_page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔍 بحث جديد", callback_data="ai_new_search"), InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_action")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    context.user_data['ai_search_page'] = page


async def ai_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التنقل بين صفحات نتائج AI"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    await show_ai_search_results(update, context, page)


async def ai_add_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة كتاب تم اختياره من نتائج AI"""
    query = update.callback_query
    await query.answer()
    
    book_index = int(query.data.split("_")[-1])
    results = context.user_data.get('ai_search_results', [])
    
    if book_index >= len(results):
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return
    
    book = results[book_index]
    
    # إضافة القسم إذا لم يكن موجوداً
    category_id = await ensure_category(book.get('category', 'عام'))
    
    # إضافة المؤلف
    success, author_id = db.add_author(book['author'], category_id)
    if not success:
        authors = db.get_authors_by_category(category_id)
        author_id = next((a[0] for a in authors if a[1].lower() == book['author'].lower()), None)
    
    if not author_id:
        await query.edit_message_text(f"❌ فشل في إضافة المؤلف: {book['author']}")
        return
    
    # إضافة الكتاب
    result = db.add_book(
        title=book['title'],
        author_id=author_id,
        description=book.get('description', ''),
        file_link=book.get('link', ''),
        added_by=update.effective_user.id
    )
    
    if result:
        await query.edit_message_text(
            f"✅ *تمت إضافة الكتاب بنجاح!*\n\n"
            f"📖 *العنوان:* {book['title']}\n"
            f"✍️ *المؤلف:* {book['author']}\n"
            f"📂 *القسم:* {book.get('category', 'عام')}\n\n"
            f"🔗 *الرابط:* {book.get('link', 'غير متوفر')}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
    else:
        await query.edit_message_text(f"❌ فشل في إضافة الكتاب: {book['title']}", reply_markup=admin_panel_keyboard())


async def ai_new_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء بحث جديد باستخدام AI"""
    query = update.callback_query
    await query.answer()
    
    # مسح البيانات القديمة
    context.user_data.pop('ai_search_results', None)
    context.user_data.pop('ai_search_page', None)
    # ==================== دوال مساعدة للذكاء الاصطناعي ====================

async def ai_suggest_books_by_mood(mood: str, books: list) -> list:
    """استخدام AI لاقتراح كتب حسب المزاج"""
    if not OPENROUTER_API_KEY:
        return []
    
    # تحضير قائمة الكتب للنموذج
    books_list = []
    for book in books:
        if isinstance(book, (list, tuple)) and len(book) > 5:
            books_list.append(f"- {book[1]} ({book[5]})")
        elif isinstance(book, dict):
            books_list.append(f"- {book.get('title', '')} ({book.get('author', '')})")
    
    if not books_list:
        return []
    
    books_text = "\n".join(books_list[:50])  # حد أقصى 50 كتاباً
    
    prompt = f"""أنت مساعد ذكي لمكتبة. المستخدم يشعر بـ "{mood}".
من قائمة الكتب التالية، اقترح 3 كتب مناسبة لمزاجه.
اختر الكتب التي تتناسب مع المزاج (مثلاً: كتب فكاهية للمزاج الحزين، كتب ملهمة للمزاج المتحمس، إلخ).

قائمة الكتب:
{books_text}

أجب فقط بأسماء الكتب وأسماء المؤلفين، كل كتاب في سطر منفصل.
مثال التنسيق:
عنوان الكتاب 1 - المؤلف 1
عنوان الكتاب 2 - المؤلف 2
عنوان الكتاب 3 - المؤلف 3
""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # استخراج الكتب المقترحة
                suggestions = []
                for line in content.strip().split('\n'):
                    if ' - ' in line:
                        title, author = line.split(' - ', 1)
                        suggestions.append((title.strip(), author.strip()))
                
                return suggestions[:3]
    except Exception as e:
        print(f"AI suggestion error: {e}")
    
    return []
async def ai_search_books(query: str) -> list:
    """البحث عن كتب باستخدام OpenRouter API"""
    if not OPENROUTER_API_KEY:
        return []
    
    prompt = f"""ابحث عن كتب حول الموضوع التالي: "{query}"
قم بتقديم 4-6 كتب مناسبة، مع المعلومات التالية لكل كتاب:
- العنوان
- المؤلف
- القسم المقترح
- وصف قصير (جملة واحدة)

استخدم التنسيق التالي لكل كتاب:
=== كتاب ===
العنوان: [العنوان]
المؤلف: [المؤلف]
القسم: [القسم]
الوصف: [الوصف القصير]
=== نهاية الكتاب ===
""
    
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.8
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # استخراج الكتب من النص
                books = []
                current_book = {}
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('العنوان:'):
                        current_book['title'] = line.replace('العنوان:', '').strip()
                    elif line.startswith('المؤلف:'):
                        current_book['author'] = line.replace('المؤلف:', '').strip()
                    elif line.startswith('القسم:'):
                        current_book['category'] = line.replace('القسم:', '').strip()
                    elif line.startswith('الوصف:'):
                        current_book['description'] = line.replace('الوصف:', '').strip()
                    elif '===' in line and current_book.get('title'):
                        books.append(current_book)
                        current_book = {}
                
                # إضافة آخر كتاب
                if current_book.get('title'):
                    books.append(current_book)
                
                return books
    except Exception as e:
        print(f"AI search error: {e}")
    
    return []
async def ensure_category(category_name: str) -> int:
    """التأكد من وجود القسم وإرجاع معرفه"""
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name.lower() == category_name.lower():
            return cat_id
    
    db.add_category(category_name)
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name.lower() == category_name.lower():
            return cat_id
    
    return 1


async def view_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل كتاب (للميزات المختلفة)"""
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    book = db.get_book_by_id(book_id)
    
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return
    
    book_id, title, file_id, file_link, downloads, author_name, category_name = book
    
    text = f"📖 *{title}*\n\n"
    text += f"✍️ *المؤلف:* {author_name}\n"
    text += f"📂 *القسم:* {category_name}\n"
    text += f"📥 *مرات التحميل:* {downloads}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📥 تحميل الكتاب", callback_data=f"download_local_{book_id}")],
        [InlineKeyboardButton("🎭 اقتراح آخر", callback_data="mood_again")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]

  async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عام للمحادثات"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu())
    else:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu())
    return ConversationHandler.END
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    # ==================== تسجيل المعالجات ====================

def register_handlers(application):
    """تسجيل جميع معالجات الميزات المتقدمة"""
    
    # محادثة طلب الكتب
    request_conv = ConversationHandler(
        entry_points=[CommandHandler("request", request_book_start)],
        states={
            WAITING_REQUEST_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_request_title)],
            WAITING_REQUEST_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_request_author)],
        },
        fallbacks=[CommandHandler("cancel", cancel_search)],
    )
    application.add_handler(request_conv)
    
    # محادثة اقتراح المزاج
    mood_conv = ConversationHandler(
        entry_points=[CommandHandler("mood", mood_suggestion_start)],
        states={
            WAITING_MOOD: [CallbackQueryHandler(mood_selected, pattern="^mood_")],
        },
        fallbacks=[CallbackQueryHandler(mood_again, pattern="^mood_again$"), CommandHandler("cancel", cancel_search)],
    )
    application.add_handler(mood_conv)
    
    # محادثة إضافة الكتب التلقائية
    ai_add_conv = ConversationHandler(
        entry_points=[CommandHandler("ai_add_books", ai_add_books_command)],
        states={
            WAITING_AI_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ai_search_query)],
            WAITING_AI_SEARCH_RESULTS: [
                CallbackQueryHandler(ai_search_page_callback, pattern="^ai_page_"),
                CallbackQueryHandler(ai_add_book_callback, pattern="^ai_add_book_"),
                CallbackQueryHandler(ai_new_search, pattern="^ai_new_search$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_search), CallbackQueryHandler(cancel_search, pattern="^cancel_action$")],
    )
    application.add_handler(ai_add_conv)
    
    # أوامر وعرض الطلبات
    application.add_handler(CommandHandler("view_requests", view_requests_command))
    application.add_handler(CallbackQueryHandler(requests_page_callback, pattern="^req_page_"))
    application.add_handler(CallbackQueryHandler(approve_request, pattern="^approve_req_"))
    application.add_handler(CallbackQueryHandler(delete_request, pattern="^delete_req_"))
    application.add_handler(CallbackQueryHandler(back_to_requests, pattern="^back_to_requests$"))
    
    # معالج عرض الكتاب
    application.add_handler(CallbackQueryHandler(view_book_callback, pattern="^view_book_"))
    
    # معالج المزاج مرة أخرى
    application.add_handler(CallbackQueryHandler(mood_again, pattern="^mood_again$"))
