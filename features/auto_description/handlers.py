from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler
from telegram.constants import ParseMode
from .services import generate_book_description
import database as db
from keyboards import cancel_only_keyboard, admin_panel_keyboard

WAITING_DESCRIPTION_APPROVAL = 1

async def generate_description_for_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطة بداية: توليد وصف مقترح بعد إدخال العنوان والمؤلف (تستدعى من admin.py بعد الإضافة)"""
    query = update.callback_query
    await query.answer()
    title = context.user_data.get("book_title")
    author_id = context.user_data.get("selected_author_id")
    if not title or not author_id:
        await query.edit_message_text("❌ لم يتم العثور على بيانات الكتاب.")
        return ConversationHandler.END
    author_data = db.get_author_by_id(author_id)
    author_name = author_data[1] if author_data else ""
    await query.edit_message_text("⏳ جارٍ توليد وصف تلقائي للكتاب...")
    description = await generate_book_description(title, author_name)
    if not description:
        await query.edit_message_text("❌ فشل توليد الوصف. سيتم إضافة الكتاب بدون وصف.")
        return ConversationHandler.END
    context.user_data["generated_description"] = description
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول الوصف", callback_data="accept_description")],
        [InlineKeyboardButton("✏️ تعديل الوصف", callback_data="edit_description")],
        [InlineKeyboardButton("❌ تخطي", callback_data="skip_description")]
    ])
    await query.edit_message_text(
        f"📝 *الوصف المقترح:*\n\n{description}\n\nهل تريد استخدام هذا الوصف؟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    return WAITING_DESCRIPTION_APPROVAL

async def handle_description_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "accept_description":
        description = context.user_data.get("generated_description")
        book_id = context.user_data.get("temp_book_id")
        if book_id and description:
            db.save_book_description(book_id, description)
        await query.edit_message_text("✅ تم حفظ الوصف بنجاح!", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END
    elif choice == "edit_description":
        await query.edit_message_text("📝 أرسل الوصف الجديد الذي تريده:", reply_markup=cancel_only_keyboard())
        return WAITING_DESCRIPTION_APPROVAL
    else:
        await query.edit_message_text("ℹ️ تم تخطي إضافة الوصف.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

async def receive_custom_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    custom_desc = update.message.text.strip()
    book_id = context.user_data.get("temp_book_id")
    if book_id:
        db.save_book_description(book_id, custom_desc)
    await update.message.reply_text("✅ تم حفظ الوصف المخصص!", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END

async def cancel_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء إضافة الوصف.", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END

description_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(generate_description_for_book, pattern="^generate_description$")],
    states={
        WAITING_DESCRIPTION_APPROVAL: [
            CallbackQueryHandler(handle_description_decision, pattern="^(accept|edit|skip)_description$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_description)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_description), CallbackQueryHandler(cancel_description, pattern="^cancel_action$")]
)

def register_handlers(application):
    application.add_handler(description_conv)
