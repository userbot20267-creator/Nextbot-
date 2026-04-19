# database.py
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
from config import DATABASE_URL, ADMIN_ID

def get_connection():
    """إنشاء وإرجاع اتصال بقاعدة البيانات"""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# ---------- إعدادات القناة ----------
def set_channel_id(channel_id: str):
    """حفظ معرف القناة للنشر التلقائي"""
    set_setting("auto_channel", channel_id)

def get_channel_id() -> str:
    """جلب معرف القناة المخزن"""
    return get_setting("auto_channel")

def set_auto_fetch_enabled(enabled: bool):
    """تفعيل/تعطيل الجلب التلقائي"""
    set_setting("auto_fetch_enabled", str(enabled).lower())

def is_auto_fetch_enabled() -> bool:
    """التحقق من تفعيل الجلب التلقائي"""
    val = get_setting("auto_fetch_enabled")
    return val == "true" if val else False

# ---------- تهيئة الجداول ----------
def init_db():
    """إنشاء جميع الجداول إذا لم تكن موجودة"""
    # إنشاء اتصال جديد خاص بالتهيئة
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    cur = conn.cursor()
    
    try:
        # 1️⃣ جدول المستخدمين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT NOW(),
                is_banned BOOLEAN DEFAULT FALSE,
                last_activity TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # إضافة عمود points
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0")
        # إضافة عمود referred_by
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT")
        
        # 2️⃣ جدول الأقسام
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # 3️⃣ جدول المؤلفين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category_id INT REFERENCES categories(id) ON DELETE CASCADE,
                UNIQUE(name, category_id)
            )
        """)
        
        # 4️⃣ جدول الكتب
        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INT REFERENCES authors(id) ON DELETE CASCADE,
                file_id TEXT,
                file_link TEXT,
                added_by BIGINT,
                download_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT")
        
        # 5️⃣ جدول الإعدادات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 6️⃣ جدول المساعدين الإداريين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY,
                added_by BIGINT NOT NULL,
                can_manage_books BOOLEAN DEFAULT FALSE,
                can_manage_categories BOOLEAN DEFAULT FALSE,
                can_manage_users BOOLEAN DEFAULT FALSE,
                can_broadcast BOOLEAN DEFAULT FALSE,
                can_view_stats BOOLEAN DEFAULT TRUE,
                can_lock_bot BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # 7️⃣ جدول المفضلة
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id BIGINT NOT NULL,
                book_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)

        # 8️⃣ جدول سجل التحميلات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                user_id BIGINT NOT NULL,
                book_id INTEGER NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id, downloaded_at),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)
        
        # 9️⃣ جدول التقييمات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id BIGINT NOT NULL,
                book_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)

        # 🔟 جدول الإحالات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL UNIQUE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        conn.commit()
    finally:
        cur.close()
        conn.close()

    # إعدادات افتراضية
    if not get_setting("auto_fetch_enabled"):
        set_auto_fetch_enabled(False)

# ---------- دوال المستخدمين ----------
def add_user(user_id: int, username: str, first_name: str, last_name: str):
    """إضافة مستخدم جديد أو تحديث بياناته إذا كان موجوداً"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_activity = NOW()
    """, (user_id, username, first_name, last_name))
    conn.commit()
    cur.close()
    conn.close()

def update_activity(user_id: int):
    """تحديث آخر نشاط للمستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_activity = NOW() WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def is_user_banned(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم محظوراً"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result['is_banned'] if result else False

def ban_user(user_id: int):
    """حظر مستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = TRUE WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def unban_user(user_id: int):
    """إلغاء حظر مستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = FALSE WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_all_users(include_banned: bool = False):
    """جلب جميع المستخدمين (للاستخدام في الإذاعة)"""
    conn = get_connection()
    cur = conn.cursor()
    if include_banned:
        cur.execute("SELECT user_id FROM users")
    else:
        cur.execute("SELECT user_id FROM users WHERE is_banned = FALSE")
    users = [row['user_id'] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users

def count_users() -> int:
    """إجمالي عدد المستخدمين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    count = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    return count

def count_active_today() -> int:
    """عدد المستخدمين النشطين اليوم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE DATE(last_activity) = CURRENT_DATE")
    count = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    return count

def count_banned_users() -> int:
    """عدد المستخدمين المحظورين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = TRUE")
    count = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    return count

def get_user_joined_date(user_id: int):
    """جلب تاريخ انضمام المستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT joined_at FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result['joined_at'] if result else None

def get_user_downloads_count(user_id: int) -> int:
    """جلب عدد مرات تحميل المستخدم للكتب (مؤقت)"""
    return 0
def get_all_users_with_details():
    """جلب جميع المستخدمين مع تفاصيلهم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, first_name, last_name, joined_at, is_banned
        FROM users ORDER BY joined_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

# ---------- دوال الأقسام ----------
def add_category(name: str) -> bool:
    """إضافة قسم جديد، ترجع True إذا نجحت"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg.errors.UniqueViolation:
        return False

def delete_category(cat_id: int):
    """حذف قسم (يحذف المؤلفين والكتب المرتبطة تلقائياً بسبب ON DELETE CASCADE)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
    conn.commit()
    cur.close()
    conn.close()

def update_category(cat_id: int, new_name: str) -> bool:
    """تعديل اسم قسم"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE categories SET name = %s WHERE id = %s", (new_name, cat_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg.errors.UniqueViolation:
        return False

def get_all_categories():
    """جلب جميع الأقسام"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = [(row['id'], row['name']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return categories

def get_category_by_id(cat_id: int):
    """جلب قسم بمعرف"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories WHERE id = %s", (cat_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return (row['id'], row['name']) if row else None

# ---------- دوال المؤلفين ----------
def add_author(name: str, category_id: int) -> tuple:
    """إضافة مؤلف، ترجع (نجاح, id)"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO authors (name, category_id) VALUES (%s, %s) RETURNING id", (name, category_id))
        author_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return True, author_id
    except psycopg.errors.UniqueViolation:
        return False, None

def get_authors_by_category(category_id: int):
    """جلب جميع مؤلفي قسم معين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM authors WHERE category_id = %s ORDER BY name", (category_id,))
    authors = [(row['id'], row['name']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return authors

def get_author_by_id(author_id: int):
    """جلب مؤلف بمعرف"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, category_id FROM authors WHERE id = %s", (author_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return (row['id'], row['name'], row['category_id']) if row else None

def delete_author(author_id: int):
    """حذف مؤلف"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM authors WHERE id = %s", (author_id,))
    conn.commit()
    cur.close()
    conn.close()

# ---------- دوال الكتب ----------
def add_book(title: str, author_id: int, file_id: str = None, file_link: str = None, added_by: int = None) -> int:
    """إضافة كتاب، ترجع معرف الكتاب الجديد"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO books (title, author_id, file_id, file_link, added_by)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (title, author_id, file_id, file_link, added_by))
    book_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    return book_id

def get_books_by_author(author_id: int):
    """جلب جميع كتب مؤلف معين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, file_id, file_link, download_count
        FROM books WHERE author_id = %s
        ORDER BY title
    """, (author_id,))
    books = [(row['id'], row['title'], row['file_id'], row['file_link'], row['download_count']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return books

def get_book_by_id(book_id: int):
    """جلب كتاب بمعرف"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
               a.name as author_name, c.name as category_name
        FROM books b
        JOIN authors a ON b.author_id = a.id
        JOIN categories c ON a.category_id = c.id
        WHERE b.id = %s
    """, (book_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return (row['id'], row['title'], row['file_id'], row['file_link'], 
                row['download_count'], row['author_name'], row['category_name'])
    return None

def delete_book(book_id: int):
    """حذف كتاب"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
    conn.commit()
    cur.close()
    conn.close()

def increment_download(book_id: int):
    """زيادة عداد تحميل كتاب"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE books SET download_count = download_count + 1 WHERE id = %s", (book_id,))
    conn.commit()
    cur.close()
    conn.close()

def search_books(query: str):
    """البحث عن الكتب بالعنوان أو المؤلف"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
               a.name as author_name, c.name as category_name
        FROM books b
        JOIN authors a ON b.author_id = a.id
        JOIN categories c ON a.category_id = c.id
        WHERE b.title ILIKE %s OR a.name ILIKE %s
        ORDER BY b.title
        LIMIT 20
    """, (f"%{query}%", f"%{query}%"))
    results = []
    for row in cur.fetchall():
        results.append((row['id'], row['title'], row['file_id'], row['file_link'],
                       row['download_count'], row['author_name'], row['category_name']))
    cur.close()
    conn.close()
    return results

def get_top_books(limit: int = 10):
    """أكثر الكتب تحميلاً"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, b.download_count, a.name as author_name
        FROM books b
        JOIN authors a ON b.author_id = a.id
        ORDER BY b.download_count DESC
        LIMIT %s
    """, (limit,))
    top = [(row['id'], row['title'], row['download_count'], row['author_name']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return top

def get_top_categories(limit: int = 5):
    """أكثر الأقسام زيارة (بناءً على تحميلات الكتب)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.name, COALESCE(SUM(b.download_count), 0) as total_downloads
        FROM categories c
        LEFT JOIN authors a ON c.id = a.category_id
        LEFT JOIN books b ON a.id = b.author_id
        GROUP BY c.id, c.name
        ORDER BY total_downloads DESC
        LIMIT %s
    """, (limit,))
    top = [(row['id'], row['name'], row['total_downloads']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return top

def get_author_id_by_book(book_id: int) -> int:
    """جلب معرف المؤلف المرتبط بكتاب"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT author_id FROM books WHERE id = %s", (book_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['author_id'] if row else None

# ---------- دوال الإعدادات ----------
def set_setting(key: str, value: str):
    """حفظ أو تحديث إعداد"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, value))
    conn.commit()
    cur.close()
    conn.close()

def get_setting(key: str) -> str:
    """جلب قيمة إعداد"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['value'] if row else None

def delete_setting(key: str):
    """حذف إعداد"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM settings WHERE key = %s", (key,))
    conn.commit()
    cur.close()
    conn.close()

def get_all_settings():
    """جلب جميع الإعدادات"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    settings = [(row['key'], row['value']) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return settings

# دوال خاصة بالقنوات الإجبارية
def get_required_channels():
    """جلب قائمة القنوات الإجبارية (باستخدام مفاتيح تبدأ بـ channel_)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key LIKE 'channel_%'")
    channels = [row['value'] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return channels

def add_required_channel(channel: str):
    """إضافة قناة إجبارية"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE key LIKE 'channel_%'")
    count = cur.fetchone()['cnt']
    key = f"channel_{count+1}"
    cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", (key, channel))
    conn.commit()
    cur.close()
    conn.close()
    return key

def remove_required_channel(channel: str):
    """حذف قناة إجبارية حسب قيمتها"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM settings WHERE value = %s", (channel,))
    conn.commit()
    cur.close()
    conn.close()

# ---------- دوال المساعدين الإداريين ----------
def add_admin(user_id: int, added_by: int, **permissions) -> bool:
    """إضافة مساعد إداري جديد مع صلاحيات محددة"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO admins (user_id, added_by, can_manage_books, can_manage_categories,
                               can_manage_users, can_broadcast, can_view_stats, can_lock_bot)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                can_manage_books = EXCLUDED.can_manage_books,
                can_manage_categories = EXCLUDED.can_manage_categories,
                can_manage_users = EXCLUDED.can_manage_users,
                can_broadcast = EXCLUDED.can_broadcast,
                can_view_stats = EXCLUDED.can_view_stats,
                can_lock_bot = EXCLUDED.can_lock_bot
        """, (
            user_id, added_by,
            permissions.get('can_manage_books', False),
            permissions.get('can_manage_categories', False),
            permissions.get('can_manage_users', False),
            permissions.get('can_broadcast', False),
            permissions.get('can_view_stats', True),
            permissions.get('can_lock_bot', False)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"خطأ في إضافة مساعد: {e}")
        return False

def remove_admin(user_id: int) -> bool:
    """حذف مساعد إداري"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id = %s", (user_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return deleted

def get_admin_permissions(user_id: int) -> dict:
    """جلب صلاحيات مساعد معين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT can_manage_books, can_manage_categories, can_manage_users,
               can_broadcast, can_view_stats, can_lock_bot
        FROM admins WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return {}
    return {
        'can_manage_books': row[0],
        'can_manage_categories': row[1],
        'can_manage_users': row[2],
        'can_broadcast': row[3],
        'can_view_stats': row[4],
        'can_lock_bot': row[5]
    }
# ---------- إعدادات مجموعة التغذية الراجعة ----------
def set_feedback_chat_id(chat_id: str):
    """حفظ معرف المجموعة لاستقبال رسائل feedback"""
    set_setting("feedback_chat_id", chat_id)

def get_feedback_chat_id() -> str:
    """جلب معرف المجموعة المخزن"""
    return get_setting("feedback_chat_id")
    
def get_all_admins():
    """جلب قائمة بجميع المساعدين الإداريين"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, added_by, added_at FROM admins ORDER BY added_at DESC")
    admins = cur.fetchall()
    cur.close()
    conn.close()
    return admins

def is_admin(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم مساعداً إدارياً (أو المالك)"""
    if user_id == ADMIN_ID:
        return True
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None
# ========== إضافات جديدة: المفضلة، سجل التحميلات، النقاط ==========

# ---------- دوال المفضلة ----------
def add_to_favorites(user_id: int, book_id: int):
    """إضافة كتاب للمفضلة"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO favorites (user_id, book_id) VALUES (%s, %s)", (user_id, book_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        cur.close()
        conn.close()

def remove_from_favorites(user_id: int, book_id: int):
    """إزالة كتاب من المفضلة"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_favorites(user_id: int):
    """جلب قائمة كتب المفضلة لمستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, a.name as author_name
        FROM favorites f
        JOIN books b ON f.book_id = b.id
        JOIN authors a ON b.author_id = a.id
        WHERE f.user_id = %s
        ORDER BY f.added_at DESC
    """, (user_id,))
    favorites = cur.fetchall()
    cur.close()
    conn.close()
    return favorites

def is_favorite(user_id: int, book_id: int) -> bool:
    """التحقق مما إذا كان الكتاب في مفضلة المستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM favorites WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

# ---------- دوال سجل التحميلات ----------
def add_download_history(user_id: int, book_id: int):
    """تسجيل عملية تحميل"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO download_history (user_id, book_id) VALUES (%s, %s)", (user_id, book_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_download_history(user_id: int):
    """جلب سجل تحميلات المستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, a.name as author_name, h.downloaded_at
        FROM download_history h
        JOIN books b ON h.book_id = b.id
        JOIN authors a ON b.author_id = a.id
        WHERE h.user_id = %s
        ORDER BY h.downloaded_at DESC
    """, (user_id,))
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history

# ---------- دوال النقاط ----------
def add_user_points(user_id: int, points: int):
    """إضافة نقاط للمستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (points, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_points(user_id: int) -> int:
    """جلب نقاط المستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['points'] if row else 0

def get_top_users_by_points(limit: int = 10):
    """أفضل المستخدمين من حيث النقاط"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, first_name, last_name, points
        FROM users
        ORDER BY points DESC
        LIMIT %s
    """, (limit,))
    top = cur.fetchall()
    cur.close()
    conn.close()
    return top
# database.py

def count_books() -> int:
    """إجمالي عدد الكتب"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM books")
            return cur.fetchone()['cnt']

def get_total_downloads() -> int:
    """إجمالي عدد التحميلات"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(download_count) as total FROM books")
            row = cur.fetchone()
            return row['total'] if row['total'] else 0

def count_books_without_description() -> int:
    """عدد الكتب التي ليس لها وصف"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM books WHERE description IS NULL OR description = ''")
            return cur.fetchone()['cnt']

def get_categories_stats(limit: int = 5) -> list:
    """إحصائيات الأقسام: عدد الكتب وإجمالي التحميلات"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.name, COUNT(b.id) as book_count, COALESCE(SUM(b.download_count), 0) as downloads
                FROM categories c
                LEFT JOIN authors a ON c.id = a.category_id
                LEFT JOIN books b ON a.id = b.author_id
                GROUP BY c.id, c.name
                ORDER BY downloads DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def get_recent_books(limit: int = 5) -> list:
    """آخر الكتب المضافة"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.title, c.name as category
                FROM books b
                JOIN authors a ON b.author_id = a.id
                JOIN categories c ON a.category_id = c.id
                ORDER BY b.created_at DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()
# تعديل دالة get_user_downloads_count لتصبح فعالة
def get_user_downloads_count(user_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM download_history WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['cnt'] if row else 0


# ---------- دوال الإحالة (Referral) ----------
def add_referral(referrer_id: int, referred_id: int):
    """تسجيل عملية إحالة جديدة"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO referrals (referrer_id, referred_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (referrer_id, referred_id)
            )
            conn.commit()


def set_user_referrer(user_id: int, referrer_id: int):
    """تعيين المُحيل للمستخدم"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET referred_by = %s WHERE user_id = %s",
                (referrer_id, user_id)
            )
            conn.commit()


def get_user_referrer(user_id: int) -> int | None:
    """جلب معرف المُحيل لمستخدم معين"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT referred_by FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row['referred_by'] if row else None

def get_user_referrals(user_id: int) -> list:
    """جلب قائمة المستخدمين الذين انضموا عبر رابط إحالة هذا المستخدم"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT referred_id, joined_at FROM referrals
                WHERE referrer_id = %s ORDER BY joined_at DESC
            """, (user_id,))
            return cur.fetchall()

def save_book_description(book_id: int, description: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE books SET description = %s WHERE id = %s", (description, book_id))
            conn.commit()
# ========== دوال جديدة للميزات المتقدمة ==========

def get_books_in_category(category_name: str) -> list:
    """جلب الكتب في قسم معين (باستخدام اسم القسم)"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.id, b.title, a.name as author
                FROM books b
                JOIN authors a ON b.author_id = a.id
                JOIN categories c ON a.category_id = c.id
                WHERE c.name = %s
            """, (category_name,))
            return cur.fetchall()


def move_book_to_category(book_id: int, new_category_id: int):
    """نقل كتاب إلى قسم جديد (ينشئ نسخة جديدة من المؤلف في القسم الجديد إذا لزم الأمر)"""
    book = get_book_by_id(book_id)
    if not book:
        return
    title = book[1]
    file_id = book[2]
    file_link = book[3]
    added_by = book[6] if len(book) > 6 else None

    author_name = book[5]
    # البحث عن المؤلف في القسم الجديد أو إنشاؤه
    authors = get_authors_by_category(new_category_id)
    author_id = None
    for aid, name in authors:
        if name.lower() == author_name.lower():
            author_id = aid
            break
    if not author_id:
        success, author_id = add_author(author_name, new_category_id)
        if not success:
            raise Exception("فشل إنشاء المؤلف في القسم الجديد")

    # حذف الكتاب القديم وإضافته من جديد
    delete_book(book_id)
    add_book(title, author_id, file_id=file_id, file_link=file_link, added_by=added_by)


def advanced_search_books(category_id=None, author_id=None, date_from=None, date_to=None,
                          file_type=None, has_description=None) -> list:
    """بحث متقدم مع فلاتر"""
    query = """
        SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
               a.name as author_name, c.name as category_name, b.created_at
        FROM books b
        JOIN authors a ON b.author_id = a.id
        JOIN categories c ON a.category_id = c.id
        WHERE 1=1
    """
    params = []
    if category_id:
        query += " AND c.id = %s"
        params.append(category_id)
    if author_id:
        query += " AND a.id = %s"
        params.append(author_id)
    if date_from:
        query += " AND b.created_at >= %s"
        params.append(date_from)
    if date_to:
        query += " AND b.created_at <= %s"
        params.append(date_to)
    if file_type == 'pdf':
        query += " AND b.file_id IS NOT NULL"
    elif file_type == 'link':
        query += " AND b.file_link IS NOT NULL"
    if has_description is True:
        query += " AND b.description IS NOT NULL AND b.description != ''"
    elif has_description is False:
        query += " AND (b.description IS NULL OR b.description = '')"

    query += " ORDER BY b.id DESC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def get_books_paginated(limit: int = 10, offset: int = 0) -> list:
    """جلب الكتب مع التصفح (لأمر /books)"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
                       a.name as author_name, c.name as category_name
                FROM books b
                JOIN authors a ON b.author_id = a.id
                JOIN categories c ON a.category_id = c.id
                ORDER BY b.id DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return cur.fetchall()
