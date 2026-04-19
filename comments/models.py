# comments/models.py
import database as db

def create_tables():
    """إنشاء جداول التعليقات والإعجابات إذا لم تكن موجودة"""
    conn = db.get_connection()
    cur = conn.cursor()
    
    # جدول التعليقات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS book_comments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            book_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    # جدول الإعجابات على التعليقات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comment_likes (
            user_id BIGINT NOT NULL,
            comment_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, comment_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (comment_id) REFERENCES book_comments(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
