# features/similar_books/services.py
import database as db

def get_similar_books(book_id: int, limit: int = 5) -> list:
    """جلب قائمة بالكتب المشابهة من نفس القسم"""
    try:
        book = db.get_book_by_id(book_id)
        if not book:
            return []

        # book: (id, title, file_id, file_link, download_count, author_name, category_name)
        # التأكد من وجود اسم القسم (الفهرس 6)
        if len(book) <= 6 or not book[6]:
            return []

        category_name = book[6]

        # جلب جميع كتب نفس القسم
        all_books_in_category = _get_books_by_category_name(category_name)
        if not all_books_in_category:
            return []

        similar = []
        for b in all_books_in_category:
            if b[0] != book_id:  # استبعاد الكتاب الحالي
                similar.append((b[0], b[1], b[5]))  # id, title, author_name
            if len(similar) >= limit:
                break

        return similar
    except Exception as e:
        print(f"خطأ في get_similar_books: {e}")
        return []

def _get_books_by_category_name(category_name: str) -> list:
    """جلب جميع الكتب في قسم معين باستخدام اسم القسم"""
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
                   a.name as author_name, c.name as category_name
            FROM books b
            JOIN authors a ON b.author_id = a.id
            JOIN categories c ON a.category_id = c.id
            WHERE c.name = %s
            ORDER BY b.download_count DESC
        """, (category_name,))
        books = cur.fetchall()
        cur.close()
        conn.close()
        return books if books else []
    except Exception as e:
        print(f"خطأ في _get_books_by_category_name: {e}")
        return []
