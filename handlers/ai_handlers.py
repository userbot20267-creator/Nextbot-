from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from services.ai_service import summarize_book_text
import database as db

async def handle_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج زر تلخيص الكتاب بالذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer("🔄 جارٍ التلخيص، انتظر قليلاً...")
    
    # استخراج معرف الكتاب من callback_data (summarize_book_16)
    try:
        book_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ معرف الكتاب غير صالح.")
        return
    
    # جلب معلومات الكتاب
    book = db.get_book_by_id(book_id)
    if not book:
        await query.message.reply_text("❌ الكتاب غير موجود.")
        return
    
    # book: (id, title, file_id, file_link, download_count, author_name, category_name)
    title = book[1]
    author = book[5]
    category = book[6]
    
    # بناء نص للتلخيص (نظراً لعدم وجود وصف، نستخدم البيانات الأساسية)
    text_to_summarize = (
        f"عنوان الكتاب: {title}\n"
        f"المؤلف: {author}\n"
        f"القسم: {category}\n"
        f"عدد التحميلات: {book[4]}"
    )
    
    await query.message.reply_text("⏳ جارٍ إرسال الطلب إلى OpenRouter...")
    
    summary = await summarize_book_text(text_to_summarize)
    
    # إرسال الملخص
    response_text = f"📖 *{title}*\n\n📝 *الملخص:*\n{summary}"
    await query.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

# تسجيل المعالج في main.py (إذا لم يكن مضافاً):
# application.add_handler(CallbackQueryHandler(handle_summarize, pattern="^summarize_book_"))
