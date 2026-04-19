# batch_upload/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_cancel_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_batch")]])

def get_confirm_batch_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ابدأ الرفع", callback_data="confirm_batch_upload")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_batch")]
    ])
