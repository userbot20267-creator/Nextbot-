# features/referral/keyboards.py
# يمكن إضافة أزرار مخصصة للإحالة في القائمة الرئيسية
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_referral_button():
    """زر الإحالة ليضاف إلى القائمة الرئيسية"""
    return InlineKeyboardButton("🎁 دعوة الأصدقاء", callback_data="referral_menu")
