import database as db
from datetime import datetime, timedelta

def get_users_with_incomplete_books():
    """جلب المستخدمين الذين حملوا كتباً ولم يقوموا بتقييمها أو إضافتها للمفضلة خلال 48 ساعة."""
    two_days_ago = datetime.now() - timedelta(days=2)
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT h.user_id, b.id as book_id, b.title
                FROM download_history h
                JOIN books b ON h.book_id = b.id
                LEFT JOIN ratings r ON h.user_id = r.user_id AND h.book_id = r.book_id
                LEFT JOIN favorites f ON h.user_id = f.user_id AND h.book_id = f.book_id
                WHERE h.downloaded_at < %s
                  AND r.book_id IS NULL
                  AND f.book_id IS NULL
                ORDER BY h.downloaded_at DESC
                LIMIT 100
            """, (two_days_ago,))
            return cur.fetchall()

def get_user_language(user_id: int) -> str:
    """تقدير لغة المستخدم (يمكن تحسينها)"""
    return "ar"  # حالياً نستخدم العربية
