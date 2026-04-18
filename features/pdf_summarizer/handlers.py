# features/pdf_summarizer/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from .services import extract_text_from_pdf, summarize_pdf_content
import database as db


async def summarize_existing_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    تلخيص كتاب موجود مسبقاً (يُستدعى عند الضغط على زر التلخيص).
    """
    query = update.callback_query
    await query.answer("🔄 جارٍ استخراج النص وتلخيصه...")

    # استخراج book_id من callback_data (مثال: summarize_pdf_123)
    try:
        book_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ معرف الكتاب غير صالح.")
        return

    # جلب معلومات الكتاب
    book = db.get_book_by_id(book_id)
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return

    file_id = book[2]  # file_id
    title = book[1]
    author = book[5]

    if not file_id:
        await query.edit_message_text("❌ هذا الكتاب لا يحتوي على ملف PDF قابل للتلخيص.")
        return

    # إرسال رسالة "جاري المعالجة"
    await query.edit_message_text(
        f"📖 *{title}*\n\n⏳ جارٍ استخراج النص من PDF...",
        parse_mode=ParseMode.MARKDOWN
    )

    # استخراج النص
    text = await extract_text_from_pdf(file_id, context)

    if not text:
        await query.edit_message_text(
            f"📖 *{title}*\n\n❌ لم يتمكن البوت من استخراج نص من هذا الملف. "
            "قد يكون الملف عبارة عن صور ممسوحة ضوئياً أو محمياً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await query.edit_message_text(
        f"📖 *{title}*\n\n⏳ جارٍ إرسال النص للتلخيص الذكي...\n"
        f"(تم استخراج {len(text)} حرف)",
        parse_mode=ParseMode.MARKDOWN
    )

    # التلخيص
    summary = await summarize_pdf_content(text, title, author)

    # حفظ الملخص في قاعدة البيانات (إذا أردت)
    # db.save_book_summary(book_id, summary)

    # عرض الملخص
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 العودة للكتاب", callback_data=f"book_{book_id}")]
    ])

    await query.edit_message_text(
        f"📖 *{title}*\n✍️ *{author}*\n\n"
        f"📝 *الملخص الذكي:*\n{summary}\n\n"
        f"💡 *هذا الملخص تم توليده آلياً بواسطة الذكاء الاصطناعي.*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


def register_handlers(application):
    """تسجيل معالجات ميزة تلخيص PDF"""
    application.add_handler(
        CallbackQueryHandler(summarize_existing_book, pattern="^summarize_pdf_")
  )
