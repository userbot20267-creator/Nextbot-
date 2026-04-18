# features/pdf_summarizer/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_summarize_button(book_id: int) -> InlineKeyboardMarkup:
    """
    إرجاع زر تلخيص PDF ليتم إضافته إلى لوحة مفاتيح تفاصيل الكتاب.
    """
    keyboard = [
        [InlineKeyboardButton("📝 تلخيص PDF (AI)", callback_data=f"summarize_pdf_{book_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
