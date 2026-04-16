from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection
from keyboards import get_book_keyboard

async def toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    book_id = int(query.data.split("_")[-1])
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if already in favorites
            cur.execute("SELECT 1 FROM favorites WHERE user_id = %s AND book_id = %s", (user_id, book_id))
            exists = cur.fetchone()
            
            if exists:
                cur.execute("DELETE FROM favorites WHERE user_id = %s AND book_id = %s", (user_id, book_id))
                msg = "❌ تمت الإزالة من المفضلة."
                is_fav = False
            else:
                cur.execute("INSERT INTO favorites (user_id, book_id) VALUES (%s, %s)", (user_id, book_id))
                msg = "❤️ تمت الإضافة إلى المفضلة بنجاح!"
                is_fav = True
            conn.commit()
    
    await query.answer(msg)
    # Update the book keyboard to reflect changes
    await query.edit_message_reply_markup(reply_markup=get_book_keyboard(book_id, is_favorite=is_fav))

async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.id, b.title 
                FROM books b 
                JOIN favorites f ON b.id = f.book_id 
                WHERE f.user_id = %s
            """, (user_id,))
            books = cur.fetchall()
            
    if not books:
        await query.answer("⚠️ ليس لديك أي كتب في المفضلة حالياً.")
        return

    text = "❤️ **قائمة الكتب المفضلة لديك:**\n\n"
    for i, book in enumerate(books, 1):
        text += f"{i}. {book['title']} (/view_{book['id']})\n"
    
    await query.message.reply_text(text, parse_mode="Markdown")
    await query.answer()

# Register handlers in main.py:
# application.add_handler(CallbackQueryHandler(toggle_favorite, pattern="^toggle_favorite_"))
# application.add_handler(CallbackQueryHandler(show_favorites, pattern="^my_favorites$"))
