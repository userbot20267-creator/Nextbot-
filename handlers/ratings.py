from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection
from keyboards import get_rating_keyboard

async def start_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    book_id = int(query.data.split("_")[-1])
    
    await query.message.edit_text(
        "⭐ **تقييم الكتاب:** يرجى اختيار عدد النجوم (1-5):",
        reply_markup=get_rating_keyboard(book_id),
        parse_mode="Markdown"
    )
    await query.answer()

async def submit_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    book_id = int(data[1])
    rating_val = int(data[2])
    user_id = query.from_user.id
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if user already rated this book
            cur.execute("SELECT 1 FROM ratings WHERE user_id = %s AND book_id = %s", (user_id, book_id))
            exists = cur.fetchone()
            
            if exists:
                cur.execute("UPDATE ratings SET rating = %s WHERE user_id = %s AND book_id = %s", (rating_val, user_id, book_id))
            else:
                cur.execute("INSERT INTO ratings (user_id, book_id, rating) VALUES (%s, %s, %s)", (user_id, book_id, rating_val))
            
            # Recalculate average rating for the book
            cur.execute("SELECT AVG(rating), COUNT(*) FROM ratings WHERE book_id = %s", (book_id,))
            avg, count = cur.fetchone()
            
            cur.execute("UPDATE books SET rating = %s, ratings_count = %s WHERE id = %s", (avg, count, book_id))
            conn.commit()
            
    await query.answer(f"✅ شكراً لتقييمك: {rating_val} نجوم!")
    # Optionally return to book view (implementation depends on view_book handler)
    await query.message.edit_text(f"⭐ تم تسجيل تقييمك ({rating_val}/5) بنجاح. شكراً لك!")

# In database.py, ensure ratings table exists:
# CREATE TABLE IF NOT EXISTS ratings (
#     user_id BIGINT REFERENCES users(user_id),
#     book_id INTEGER REFERENCES books(id),
#     rating INTEGER CHECK (rating >= 1 AND rating <= 5),
#     PRIMARY KEY (user_id, book_id)
# )
