from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from .services import get_users_with_incomplete_books

async def send_reminders(bot: Bot):
    reminders = get_users_with_incomplete_books()
    # تجميع حسب المستخدم
    user_books = {}
    for user_id, book_id, title in reminders:
        if user_id not in user_books:
            user_books[user_id] = []
        if len(user_books[user_id]) < 3:  # حد أقصى 3 كتب لكل مستخدم
            user_books[user_id].append((book_id, title))
    for user_id, books in user_books.items():
        if not books:
            continue
        text = "📚 *تذكير قراءة*\n\nلديك كتب قمت بتحميلها ولم تكملها بعد:\n"
        keyboard = []
        for book_id, title in books:
            text += f"• {title}\n"
            keyboard.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"book_{book_id}")])
        keyboard.append([InlineKeyboardButton("📚 تصفح المكتبة", callback_data="browse_categories")])
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"فشل إرسال تذكير لـ {user_id}: {e}")
