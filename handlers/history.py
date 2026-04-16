from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.id, b.title, h.downloaded_at 
                FROM books b 
                JOIN download_history h ON b.id = h.book_id 
                WHERE h.user_id = %s 
                ORDER BY h.downloaded_at DESC 
                LIMIT 10
            """, (user_id,))
            history = cur.fetchall()
            
    if not history:
        await query.answer("⚠️ لا يوجد لديك سجل تحميلات حالياً.")
        return

    text = "📜 **آخر 10 كتب قمت بتحميلها:**\n\n"
    for i, item in enumerate(history, 1):
        date = item['downloaded_at'].strftime("%Y-%m-%d %H:%M")
        text += f"{i}. {item['title']} - {date} (/view_{item['id']})\n"
    
    await query.message.reply_text(text, parse_mode="Markdown")
    await query.answer()

async def log_download(user_id: int, book_id: int):
    """Utility function to log a download in the database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO download_history (user_id, book_id) 
                VALUES (%s, %s)
            """, (user_id, book_id))
            conn.commit()

# Register handlers in main.py:
# application.add_handler(CallbackQueryHandler(show_history, pattern="^my_history$"))
