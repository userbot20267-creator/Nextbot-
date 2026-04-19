# features/describe_existing/keyboards.py
from telegram import InlineKeyboardButton


def get_describe_button(book_id: int) -> InlineKeyboardButton:
    """
    إرجاع زر 'توليد وصف' ليتم إضافته إلى لوحة مفاتيح تفاصيل الكتاب.

    Args:
        book_id: معرف الكتاب المراد توليد وصف له.

    Returns:
        InlineKeyboardButton مع callback_data مناسب.
    """
    return InlineKeyboardButton(
        text="🤖 توليد وصف",
        callback_data=f"describe_existing_{book_id}"
    )
