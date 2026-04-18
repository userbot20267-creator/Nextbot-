from telegram import InlineKeyboardButton

def get_suggest_category_button():
    return InlineKeyboardButton("🤖 اقتراح قسم تلقائي", callback_data="suggest_category")
