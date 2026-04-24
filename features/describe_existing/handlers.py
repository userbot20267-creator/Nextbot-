# features/describe_existing/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)
from telegram.constants import ParseMode
import database as db
from .services import generate_description
from keyboards import cancel_only_keyboard

# حالة المحادثة
WAITING_DESCRIPTION = 1


async def describe_existing_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطة البداية: توليد وصف لكتاب موجود (تستدعى عند الضغط على زر 'توليد وصف')"""
    query = update.callback_query
    await query.answer()

    # استخراج book_id من callback_data (مثال: describe_existing_123)
    try:
        book_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ معرف الكتاب غير صالح.")
        return ConversationHandler.END

    # جلب معلومات الكتاب
    book = db.get_book_by_id(book_id)
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return ConversationHandler.END

    # تخزين المعلومات في user_data
    context.user_data["desc_book_id"] = book_id
    context.user_data["desc_title"] = book[1]      # title
    context.user_data["desc_author"] = book[5]     # author_name

    await query.edit_message_text(
        f"🤖 *جاري توليد وصف لـ* _{book[1]}_ ...",
        parse_mode=ParseMode.MARKDOWN
    )

    # توليد الوصف باستخدام الذكاء الاصطناعي
    description = await generate_description(book[1], book[5])
    context.user_data["generated_desc"] = description

    # عرض الوصف مع أزرار القبول / التعديل / الإلغاء
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول الوصف", callback_data="accept_desc")],
        [InlineKeyboardButton("✏️ تعديل الوصف", callback_data="edit_desc")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")]
    ])

    await query.edit_message_text(
        f"📝 *الوصف المقترح:*\n\n{description}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    return WAITING_DESCRIPTION


async def handle_description_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار المستخدم (قبول، تعديل، إلغاء)"""
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "accept_desc":
        # حفظ الوصف المقترح
        book_id = context.user_data.get("desc_book_id")
        description = context.user_data.get("generated_desc")
        if book_id and description:
            db.save_book_description(book_id, description)
            await query.edit_message_text("✅ *تم حفظ الوصف بنجاح!*", parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text("❌ حدث خطأ أثناء حفظ الوصف.")
        return ConversationHandler.END

    elif choice == "edit_desc":
        # الانتقال إلى وضع إدخال وصف مخصص
        await query.edit_message_text(
            "✏️ *أرسل الوصف الجديد الذي تريده:*\n\n(يمكنك إرسال /cancel للإلغاء)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_only_keyboard()
        )
        return WAITING_DESCRIPTION

    else:  # cancel_desc
        await query.edit_message_text("❌ *تم إلغاء إضافة الوصف.*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END


async def receive_custom_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الوصف المخصص من المستخدم وحفظه"""
    book_id = context.user_data.get("desc_book_id")
    custom_desc = update.message.text.strip()

    if not book_id:
        await update.message.reply_text("❌ حدث خطأ، لم يتم العثور على الكتاب.")
        return ConversationHandler.END

    db.save_book_description(book_id, custom_desc)
    await update.message.reply_text(
        "✅ *تم حفظ الوصف المخصص بنجاح!*",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


async def cancel_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية من قبل المستخدم"""
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ *تم إلغاء العملية.*", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ *تم إلغاء العملية.*", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def register_handlers(application):
    """تسجيل محادثة توليد الوصف للكتب الموجودة"""
    description_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(describe_existing_book, pattern="^describe_existing_")
        ],
        states={
            WAITING_DESCRIPTION: [
                CallbackQueryHandler(handle_description_decision, pattern="^(accept|edit|cancel)_desc$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_description),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_description, pattern="^cancel_action$"),
            CommandHandler("cancel", cancel_description),
        ],
    )
    application.add_handler(description_conv)
