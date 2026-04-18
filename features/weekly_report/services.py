# features/weekly_report/services.py
import database as db
from datetime import datetime, timedelta

def get_weekly_stats():
    """جمع إحصائيات الأسبوع الحالي"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    # مستخدمين جدد هذا الأسبوع
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM users 
                WHERE joined_at >= %s
            """, (week_ago,))
            new_users = cur.fetchone()['count']
            
            # إجمالي التحميلات هذا الأسبوع
            cur.execute("""
                SELECT COUNT(*) FROM download_history 
                WHERE downloaded_at >= %s
            """, (week_ago,))
            weekly_downloads = cur.fetchone()['count']
            
            # أكثر 5 كتب تحميلاً هذا الأسبوع
            cur.execute("""
                SELECT b.title, COUNT(*) as cnt
                FROM download_history h
                JOIN books b ON h.book_id = b.id
                WHERE h.downloaded_at >= %s
                GROUP BY b.id, b.title
                ORDER BY cnt DESC
                LIMIT 5
            """, (week_ago,))
            top_books = cur.fetchall()
            
            # أكثر الأقسام نشاطاً (تحميلات)
            cur.execute("""
                SELECT c.name, COUNT(*) as cnt
                FROM download_history h
                JOIN books b ON h.book_id = b.id
                JOIN authors a ON b.author_id = a.id
                JOIN categories c ON a.category_id = c.id
                WHERE h.downloaded_at >= %s
                GROUP BY c.id, c.name
                ORDER BY cnt DESC
                LIMIT 3
            """, (week_ago,))
            top_categories = cur.fetchall()
            
            # إجمالي المستخدمين
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()['count']
            
            # إجمالي الكتب
            cur.execute("SELECT COUNT(*) FROM books")
            total_books = cur.fetchone()['count']
    
    return {
        "week_ago": week_ago,
        "today": today,
        "new_users": new_users,
        "weekly_downloads": weekly_downloads,
        "top_books": top_books,
        "top_categories": top_categories,
        "total_users": total_users,
        "total_books": total_books,
  }
