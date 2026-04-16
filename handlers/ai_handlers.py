from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection
from services.ai_service import summarize_book_text

async def handle_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    book_id = int(query.data.split("_")[-1])
    
    # Get book info from database
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT title, description FROM books WHERE id = %s", (book_id,))
            book = cur.fetchone()
            
    if not book:
        await query.answer("❌ عذراً، لم يتم العثور على معلومات الكتاب.")
        return

    await query.answer("🔄 جاري التلخيص بالذكاء الاصطناعي... يرجى الانتظار قليلاً. ⏳")
    
    # Call AI Service
    summary = await summarize_book_text(book['title'], book['description'])
    
    # Send the summary
    text = f"📝 **ملخص كتاب: {book['title']}**\n\n{summary}\n\n"
    text += "💡 *هذا الملخص تم توليده آلياً بواسطة الذكاء الاصطناعي.*"
    
    await query.message.reply_text(text, parse_mode="Markdown")

# Register handler in main.py:
# application.add_handler(CallbackQueryHandler(handle_summarize, pattern="^summarize_book_"))
