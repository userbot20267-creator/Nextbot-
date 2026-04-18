# features/similar_books/services.py
import database as db


def get_similar_books(book_id: int, limit: int = 5) -> list:
    """
    جلب قائمة بالكتب المشابهة من نفس القسم.
    
    Args:
        book_id: معرف الكتاب الحالي
        limit: عدد الكتب المشابهة المطلوبة
    
    Returns:
        قائمة بالكتب المشابهة، كل عنصر: (id, title, author_name)
    """
    book = db.get_book_by_id(book_id)
    if not book:
        return []

    # جلب معرف القسم من خلال المؤلف
    author_id = db.get_author_id_by_book(book_id)
    if not author_id:
        return []

    author = db.get_author_by_id(author_id)
    if not author:
        return []

    category_id = author[2]

    # جلب جميع كتب القسم (تحتاج دالة جديدة في database.py)
    all_books = _get_books_by_category(category_id)

    similar = []
    for b in all_books:
        if b[0] != book_id:  # استبعاد الكتاب الحالي
            similar.append((b[0], b[1], b[5]))  # id, title, author_name
        if len(similar) >= limit:
            break

    return similar


def _get_books_by_category(category_id: int) -> list:
    """
    دالة مساعدة: جلب جميع الكتب في قسم معين.
    """
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.title, b.file_id, b.file_link, b.download_count,
               a.name as author_name, c.name as category_name
        FROM books b
        JOIN authors a ON b.author_id = a.id
        JOIN categories c ON a.category_id = c.id
        WHERE c.id = %s
        ORDER BY b.download_count DESC
    """, (category_id,))
    books = cur.fetchall()
    cur.close()
    conn.close()
    return books
