# comments/services.py
import database as db

def add_comment(user_id: int, book_id: int, text: str) -> int | None:
    """إضافة تعليق، ترجع معرف التعليق أو None"""
    if len(text) > 500:
        text = text[:497] + "..."
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO book_comments (user_id, book_id, text) VALUES (%s, %s, %s) RETURNING id",
            (user_id, book_id, text)
        )
        comment_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return comment_id
    except Exception as e:
        print(f"خطأ في إضافة تعليق: {e}")
        return None

def get_book_comments(book_id: int, limit: int = 10, offset: int = 0, user_id: int = None) -> list:
    """جلب تعليقات كتاب معين مع عدد الإعجابات وحالة إعجاب المستخدم الحالي"""
    conn = db.get_connection()
    cur = conn.cursor()
    
    if user_id is not None:
        cur.execute("""
            SELECT c.id, c.user_id, c.text, c.created_at,
                   u.first_name, u.username,
                   (SELECT COUNT(*) FROM comment_likes l WHERE l.comment_id = c.id) as likes_count,
                   EXISTS(SELECT 1 FROM comment_likes l WHERE l.comment_id = c.id AND l.user_id = %s) as liked_by_user
            FROM book_comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.book_id = %s
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, book_id, limit, offset))
    else:
        cur.execute("""
            SELECT c.id, c.user_id, c.text, c.created_at,
                   u.first_name, u.username,
                   (SELECT COUNT(*) FROM comment_likes l WHERE l.comment_id = c.id) as likes_count,
                   FALSE as liked_by_user
            FROM book_comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.book_id = %s
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
        """, (book_id, limit, offset))
    
    comments = cur.fetchall()
    cur.close()
    conn.close()
    return comments if comments else []

def toggle_like(user_id: int, comment_id: int) -> tuple[bool, int]:
    """تبديل الإعجاب على تعليق، ترجع (هل هو معجب الآن, عدد الإعجابات الجديد)"""
    conn = db.get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT 1 FROM comment_likes WHERE user_id = %s AND comment_id = %s", (user_id, comment_id))
    exists = cur.fetchone()
    
    if exists:
        cur.execute("DELETE FROM comment_likes WHERE user_id = %s AND comment_id = %s", (user_id, comment_id))
        liked = False
    else:
        cur.execute("INSERT INTO comment_likes (user_id, comment_id) VALUES (%s, %s)", (user_id, comment_id))
        liked = True
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id = %s", (comment_id,))
    count = cur.fetchone()['cnt']
    
    cur.close()
    conn.close()
    return liked, count

def delete_comment(comment_id: int, user_id: int, is_admin: bool = False) -> bool:
    """حذف تعليق"""
    conn = db.get_connection()
    cur = conn.cursor()
    if is_admin:
        cur.execute("DELETE FROM book_comments WHERE id = %s", (comment_id,))
    else:
        cur.execute("DELETE FROM book_comments WHERE id = %s AND user_id = %s", (comment_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return deleted
