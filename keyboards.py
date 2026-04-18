# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ---------- القوائم الرئيسية للمستخدم العادي ----------
def main_menu():
    """القائمة الرئيسية للمستخدم العادي - تم تحديثها لتشمل الميزات الجديدة"""
    keyboard = [
        [InlineKeyboardButton("📚 تصفح الأقسام", callback_data="browse_categories")],
        [InlineKeyboardButton("🔍 بحث عن كتاب", callback_data="search_prompt")],
        [InlineKeyboardButton("❤️ المفضلة", callback_data="my_favorites"), 
         InlineKeyboardButton("📜 سجل التحميلات", callback_data="my_history")],
        [InlineKeyboardButton("🏆 لوحة الشرف (النقاط)", callback_data="my_points")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main_button():
    """زر العودة للقائمة الرئيسية (يستخدم في نهاية القوائم)"""
    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)

# ---------- أزرار التصفح الشجري (أقسام -> مؤلفين -> كتب) ----------
def categories_keyboard(categories, page: int = 0, items_per_page: int = 5):
    """
    عرض قائمة الأقسام مع ترقيم صفحات بسيط (اختياري).
    categories: قائمة من tuples (id, name)
    """
    start = page * items_per_page
    end = start + items_per_page
    page_categories = categories[start:end]
    
    keyboard = []
    for cat_id, cat_name in page_categories:
        keyboard.append([InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}")])
    
    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"catpage_{page-1}"))
    if end < len(categories):
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"catpage_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def authors_keyboard(authors, category_id: int, page: int = 0, items_per_page: int = 5):
    """عرض مؤلفي قسم معين"""
    start = page * items_per_page
    end = start + items_per_page
    page_authors = authors[start:end]
    
    keyboard = []
    for author_id, author_name in page_authors:
        keyboard.append([InlineKeyboardButton(author_name, callback_data=f"author_{author_id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"authpage_{category_id}_{page-1}"))
    if end < len(authors):
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"authpage_{category_id}_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 العودة للأقسام", callback_data="browse_categories")])
    return InlineKeyboardMarkup(keyboard)

def books_keyboard(books, author_id: int):
    """عرض كتب مؤلف معين"""
    keyboard = []
    for book_id, title, file_id, file_link, downloads in books:
        # نستخدم callback_data يحتوي على book_id وعملية التحميل
        keyboard.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"book_{book_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 العودة للمؤلفين", callback_data=f"back_authors_{author_id}")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def book_detail_keyboard(book_id: int, file_id: str = None, file_link: str = None, is_favorite: bool = False):
    """أزرار تفاصيل الكتاب: تحميل، مفضلة، تقييم، تلخيص - [محدثة]"""
    keyboard = []
    
    # صف التحميل
    if file_id:
        keyboard.append([InlineKeyboardButton("📥 تحميل الكتاب", callback_data=f"download_{book_id}")])
    elif file_link:
        keyboard.append([InlineKeyboardButton("🔗 رابط خارجي", url=file_link)])
    
    # صف المفضلة والتقييم
    fav_text = "❤️ إزالة من المفضلة" if is_favorite else "🤍 إضافة للمفضلة"
    keyboard.append([
        InlineKeyboardButton(fav_text, callback_data=f"toggle_favorite_{book_id}"),
        InlineKeyboardButton("⭐ تقييم", callback_data=f"rate_book_{book_id}")
    ])
    
    # صف التلخيص
    keyboard.append([InlineKeyboardButton("📝 تلخيص الكتاب (AI)", callback_data=f"summarize_book_{book_id}")])
    
    # صف كتب مشابهة (جديد)
    keyboard.append([InlineKeyboardButton("📚 كتب مشابهة", callback_data=f"similar_books_{book_id}")])
    # صف مشاركة (جديد)
    keyboard.append([InlineKeyboardButton("🔗 مشاركة الكتاب", callback_data=f"share_book_{book_id}")])
    keyboard.append([InlineKeyboardButton("🔙 العودة للكتب", callback_data=f"back_books_{book_id}")])
    return InlineKeyboardMarkup(keyboard)

# ---------- أزرار التقييم الجديدة ----------
def get_rating_keyboard(book_id):
    """أزرار اختيار التقييم من 1 إلى 5"""
    keyboard = [[InlineKeyboardButton(str(i), callback_data=f"rate_{book_id}_{i}") for i in range(1, 6)]]
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"book_{book_id}")])
    return InlineKeyboardMarkup(keyboard)

# ---------- أزرار البحث ----------
def search_prompt_keyboard():
    """زر إلغاء البحث"""
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_search")]]
    return InlineKeyboardMarkup(keyboard)

def search_results_keyboard(results):
    """عرض نتائج البحث (داخلية + خارجية)"""
    keyboard = []
    for idx, book in enumerate(results):
        # book قد يكون من قاعدة البيانات أو من API خارجي
        if len(book) >= 4:  # من قاعدة البيانات: (id, title, file_id, file_link, downloads, author, category)
            book_id = book[0]
            title = book[1]
            author = book[5]
            keyboard.append([InlineKeyboardButton(f"{title} - {author}", callback_data=f"book_{book_id}")])
        else:  # نتيجة خارجية: (title, author, link)
            title, author, link = book
            keyboard.append([InlineKeyboardButton(f"{title} - {author} (خارجي)", url=link)])
    
    keyboard.append([InlineKeyboardButton("🔍 بحث جديد", callback_data="search_prompt")])
    keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ---------- لوحة تحكم المالك (/admin) ----------
def admin_panel_keyboard():
    """القائمة الرئيسية للوحة التحكم - تم تحديثها"""
    keyboard = [
        [InlineKeyboardButton("📁 إدارة الأقسام", callback_data="admin_categories")],
        [InlineKeyboardButton("📚 إدارة الكتب", callback_data="admin_books")],
        [InlineKeyboardButton("📢 إدارة القنوات الإجبارية", callback_data="admin_channels")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
         InlineKeyboardButton("📥 تصدير CSV", callback_data="admin_export_users")],
        [InlineKeyboardButton("📣 إذاعة رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔍 بحث وإضافة كتاب", callback_data="admin_search_add_book")],
        [InlineKeyboardButton("📝 تخصيص الرسائل", callback_data="admin_custom_msgs")],
        [InlineKeyboardButton("🤖 أدوات ذكاء اصطناعي", callback_data="admin_ai_tools")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- أقسام الإدارة الفرعية ---
def admin_categories_keyboard(categories):
    """عرض الأقسام مع خيارات إدارة"""
    keyboard = []
    for cat_id, name in categories:
        keyboard.append([
            InlineKeyboardButton(name, callback_data=f"adm_cat_{cat_id}"),
            InlineKeyboardButton("❌ حذف", callback_data=f"adm_delcat_{cat_id}")
        ])
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="admin_add_category")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)

def admin_category_actions_keyboard(cat_id: int):
    """خيارات تعديل/حذف قسم محدد"""
    keyboard = [
        [InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"adm_editcat_{cat_id}")],
        [InlineKeyboardButton("📚 إدارة الكتب", callback_data=f"adm_bookscat_{cat_id}")],
        [InlineKeyboardButton("❌ حذف القسم", callback_data=f"adm_delcat_{cat_id}")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="admin_categories")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_books_management_keyboard():
    """قائمة إدارة الكتب"""
    keyboard = [
        [InlineKeyboardButton("➕ إضافة كتاب يدوي", callback_data="admin_add_book_manual")],
        [InlineKeyboardButton("✏️ تعديل كتاب", callback_data="admin_edit_book")],
        [InlineKeyboardButton("❌ حذف كتاب", callback_data="admin_delete_book")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_users_keyboard():
    """قائمة إدارة المستخدمين - تم تحديثها"""
    keyboard = [
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user")],
        [InlineKeyboardButton("✅ فك الحظر", callback_data="admin_unban_user")],
        [InlineKeyboardButton("👁 عرض المحظورين", callback_data="admin_banned_list")],
        [InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="admin_user_stats")],
        [InlineKeyboardButton("👥 عرض جميع المستخدمين", callback_data="admin_users_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_channels_keyboard(channels):
    """عرض القنوات الإجبارية مع إمكانية الحذف"""
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(ch, callback_data=f"adm_ch_{ch}"),
            InlineKeyboardButton("❌ حذف", callback_data=f"adm_delch_{ch}")
        ])
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)

def admin_stats_keyboard():
    """قائمة الإحصائيات"""
    keyboard = [
        [InlineKeyboardButton("📈 أكثر الكتب تحميلاً", callback_data="admin_top_books")],
        [InlineKeyboardButton("📊 أكثر الأقسام زيارة", callback_data="admin_top_categories")],
        [InlineKeyboardButton("👥 إحصائيات المستخدمين", callback_data="admin_user_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)
def admin_ai_tools_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 توليد وصف تلقائي", callback_data="generate_description")],
        [InlineKeyboardButton("📂 اقتراح قسم تلقائي", callback_data="suggest_category")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)
# ---------- أزرار الاشتراك الإجباري ----------
def subscription_required_keyboard(channels):
    """يُعرض للمستخدم الذي لم يشترك في القنوات المطلوبة"""
    keyboard = []
    for idx, channel in enumerate(channels):
        # إضافة زر لكل قناة
        if channel.startswith('@'):
            url = f"https://t.me/{channel[1:]}"
        else:
            url = f"https://t.me/{channel}"  # في حال كان معرف القناة بدون @
        keyboard.append([InlineKeyboardButton(f"📢 اشترك في القناة {idx+1}", url=url)])
    
    keyboard.append([InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)

# ---------- أزرار عامة (إلغاء، تأكيد) ----------
def confirm_cancel_keyboard(action: str = ""):
    """زري تأكيد وإلغاء"""
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def cancel_only_keyboard():
    """زر إلغاء فقط (لحالات إدخال النص)"""
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")]]
    return InlineKeyboardMarkup(keyboard)

# ---------- أزرار إدارة الكتب من داخل القسم ----------
def admin_category_books_keyboard(cat_id: int):
    """أزرار إدارة الكتب المرتبطة بقسم معين"""
    keyboard = [
        [InlineKeyboardButton("➕ إضافة كتاب للقسم", callback_data=f"adm_addbook_cat_{cat_id}")],
        [InlineKeyboardButton("📋 عرض كتب القسم", callback_data=f"adm_listbooks_cat_{cat_id}")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="admin_categories")],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_select_author_keyboard(authors, cat_id: int):
    """عرض قائمة المؤلفين لاختيار مؤلف عند إضافة كتاب"""
    keyboard = []
    for author_id, author_name in authors:
        keyboard.append([InlineKeyboardButton(author_name, callback_data=f"adm_selauthor_{author_id}_{cat_id}")])
    keyboard.append([InlineKeyboardButton("➕ إضافة مؤلف جديد", callback_data=f"adm_newauthor_{cat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"adm_cat_{cat_id}")])
    return InlineKeyboardMarkup(keyboard)
def get_book_keyboard(book_id: int, is_favorite: bool = False):
    """
    واجهة متوافقة مع الاستدعاءات القديمة.
    تقوم بجلب معلومات الكتاب من قاعدة البيانات لإنشاء لوحة المفاتيح.
    """
    from database import get_connection  # استيراد محلي لتجنب الدوران
    
    file_id = None
    file_link = None
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT file_id, file_link FROM books WHERE id = %s", (book_id,))
            row = cur.fetchone()
            if row:
                file_id = row['file_id']    # ✅ استخدم المفتاح بدلاً من الفهرس
                file_link = row['file_link'] # ✅ استخدم المفتاح بدلاً من الفهرس
    
    return book_detail_keyboard(book_id, file_id, file_link, is_favorite)
