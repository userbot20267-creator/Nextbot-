# comments/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def comments_menu_keyboard(book_id: int):
    """أزرار قائمة التعليقات"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ أضف تعليق", callback_data="add_comment")],
        [InlineKeyboardButton("🔙 العودة للكتاب", callback_data=f"book_{book_id}")]
    ])

def get_comment_button(book_id: int):
    """زر عرض التعليقات في تفاصيل الكتاب"""
    return InlineKeyboardButton("💬 التعليقات", callback_data=f"comments_{book_id}")
