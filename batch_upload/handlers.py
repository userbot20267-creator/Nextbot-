# batch_upload/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
import database as db
from config import ADMIN_ID
from .services import process_batch_files
from .keyboards import get_cancel_button, get_confirm_batch_keyboard

WAITING_FILES, WAITING_CATEGORY, WAITING_AUTHOR, CONFIRM_BATCH = range(4)

async def batch_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمالك فقط.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📦 *الرفع الدفعي المباشر*\n\n"
        "أرسل لي *ملفات PDF* التي تريد إضافتها دفعة واحدة.\n"
        "يمكنك إرسال عدة ملفات في رسالة واحدة.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_cancel_button()
    )
    return WAITING_FILES

async def receive_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("❌ يرجى إرسال ملفات PDF فقط.")
        return WAITING_FILES
    
    # يمكن استقبال عدة ملفات في نفس الرسالة (media_group)
    # للتبسيط هنا نستقبل ملفاً واحداً، يمكن تطويرها لاحقاً
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name or "unknown.pdf"
    
    if "batch_files" not in context.user_data:
        context.user_data["batch_files"] = []
    
    context.user_data["batch_files"].append({"file_id": file_id, "file_name": file_name})
    
    await update.message.reply_text(
        f"✅ تم استلام: {file_name}\n"
        "أرسل المزيد من الملفات أو اضغط /done للمتابعة.\n"
        "أو /cancel للإلغاء."
    )
    return WAITING_FILES

async def done_receiving(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الانتقال لاختيار القسم"""
    files = context.user_data.get("batch_files", [])
    if not files:
        await update.message.reply_text("❌ لم يتم استلام أي ملفات.")
        return ConversationHandler.END
    
    categories = db.get_all_categories()
    keyboard = []
    for cat_id, name in categories:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"batch_cat_{cat_id}")])
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_batch")])
    
    await update.message.reply_text(
        f"📁 تم استلام {len(files)} ملفات.\nاختر القسم الذي تريد حفظها فيه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_CATEGORY

async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[-1])
    context.user_data["batch_cat_id"] = cat_id
    
    authors = db.get_authors_by_category(cat_id)
    keyboard = []
    for auth_id, name in authors:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"batch_auth_{auth_id}")])
    keyboard.append([InlineKeyboardButton("➕ إضافة مؤلف جديد", callback_data="batch_new_author")])
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_batch")])
    
    await query.edit_message_text(
        "✍️ اختر المؤلف (سيتم حفظ جميع الكتب باسمه):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_AUTHOR

async def select_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "batch_new_author":
        await query.edit_message_text("✍️ أرسل اسم المؤلف الجديد:")
        return WAITING_AUTHOR
    
    author_id = int(query.data.split("_")[-1])
    context.user_data["batch_auth_id"] = author_id
    return await confirm_batch(update, context)

async def confirm_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("batch_files", [])
    cat_id = context.user_data.get("batch_cat_id")
    auth_id = context.user_data.get("batch_auth_id")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"📦 *تأكيد الرفع الدفعي*\n\n"
            f"عدد الملفات: {len(files)}\n"
            f"القسم: {cat_id}\n"
            f"المؤلف: {auth_id}\n\n"
            f"سيتم استخراج عنوان كل كتاب من اسم الملف.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_confirm_batch_keyboard()
        )
    return CONFIRM_BATCH

async def execute_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ جاري الرفع...")
    
    files = context.user_data.get("batch_files", [])
    cat_id = context.user_data.get("batch_cat_id")
    auth_id = context.user_data.get("batch_auth_id")
    
    success, failed = await process_batch_files(files, cat_id, auth_id)
    
    await query.edit_message_text(
        f"✅ اكتمل الرفع الدفعي!\n"
        f"📚 تمت إضافة {success} كتاباً بنجاح.\n"
        f"❌ فشل: {failed}"
    )
    return ConversationHandler.END

def register_handlers(application):
    batch_conv = ConversationHandler(
        entry_points=[CommandHandler("batch", batch_upload_start)],
        states={
            WAITING_FILES: [
                MessageHandler(filters.Document.ALL, receive_files),
                CommandHandler("done", done_receiving)
            ],
            WAITING_CATEGORY: [CallbackQueryHandler(select_category, pattern="^batch_cat_")],
            WAITING_AUTHOR: [
                CallbackQueryHandler(select_author, pattern="^batch_auth_"),
                CallbackQueryHandler(select_author, pattern="^batch_new_author$")
            ],
            CONFIRM_BATCH: [CallbackQueryHandler(execute_batch, pattern="^confirm_batch_upload$")]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END),
                   CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^cancel_batch$")]
    )
    application.add_handler(batch_conv)
