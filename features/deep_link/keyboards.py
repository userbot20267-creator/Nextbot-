# features/deep_link/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_share_button(book_id: int) -> InlineKeyboardMarkup:
    """
    إرجاع زر "مشاركة" ليتم إضافته إلى لوحة مفاتيح تفاصيل الكتاب.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 مشاركة الكتاب", callback_data=f"share_book_{book_id}")]
    ])
