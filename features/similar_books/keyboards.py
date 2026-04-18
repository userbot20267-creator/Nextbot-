# features/similar_books/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_similar_books_button(book_id: int) -> InlineKeyboardMarkup:
    """
    إرجاع زر "كتب مشابهة" ليتم إضافته إلى لوحة مفاتيح تفاصيل الكتاب.
    """
    keyboard = [
        [InlineKeyboardButton("📚 كتب مشابهة", callback_data=f"similar_books_{book_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
