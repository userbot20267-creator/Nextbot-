from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_generate_description_button():
    return InlineKeyboardButton("🤖 توليد وصف تلقائي", callback_data="generate_description")
