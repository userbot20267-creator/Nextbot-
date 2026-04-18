from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler
from telegram.constants import ParseMode
from .services import suggest_category
import database as db
from keyboards import cancel_only_keyboard

WAITING_CATEGORY_APPROVAL = 1

async def suggest_category_for_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = context.user_data.get("book_title")
    author_id = context.user_data.get("selected_author_id")
    if not title or not author_id:
        await query.edit_message_text("❌ بيانات الكتاب غير مكتملة.")
        return ConversationHandler.END
    author_data = db.get_author_by_id(author_id)
    author_name = author_data[1] if author_data else ""
    categories = db.get_all_categories()
    if not categories:
        await query.edit_message_text("❌ لا توجد أقسام.")
        return ConversationHandler.END
    await query.edit_message_text("🤖 جارٍ تحليل الكتاب واقتراح قسم مناسب...")
    suggestion = await suggest_category(title, author_name, categories)
    if not suggestion:
        await query.edit_message_text("❌ فشل الاقتراح. اختر القسم يدوياً.")
        return ConversationHandler.END
    cat_id = None
    for cid, cname in categories:
        if cname.lower() == suggestion.lower():
            cat_id = cid
            break
    if not cat_id:
        await query.edit_message_text(f"❌ القسم '{suggestion}' غير موجود في القائمة.")
        return ConversationHandler.END
    context.user_data["suggested_cat_id"] = cat_id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول الاقتراح", callback_data="accept_category")],
        [InlineKeyboardButton("📂 اختيار قسم آخر", callback_data="choose_other_category")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")]
    ])
    await query.edit_message_text(
        f"📁 *القسم المقترح:* {suggestion}\nهل تريد استخدامه؟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    return WAITING_CATEGORY_APPROVAL

async def handle_category_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "accept_category":
        cat_id = context.user_data.get("suggested_cat_id")
        context.user_data["target_cat_id"] = cat_id
        await query.edit_message_text("✅ تم اعتماد القسم المقترح.")
        return ConversationHandler.END
    elif query.data == "choose_other_category":
        categories = db.get_all_categories()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(name, callback_data=f"manual_cat_{cid}")] for cid, name in categories
        ] + [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")]])
        await query.edit_message_text("اختر القسم المناسب:", reply_markup=keyboard)
        return WAITING_CATEGORY_APPROVAL
    else:
        await query.edit_message_text("❌ تم إلغاء الاقتراح.")
        return ConversationHandler.END

async def manual_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[-1])
    context.user_data["target_cat_id"] = cat_id
    await query.edit_message_text("✅ تم تحديد القسم.")
    return ConversationHandler.END

category_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(suggest_category_for_book, pattern="^suggest_category$")],
    states={
        WAITING_CATEGORY_APPROVAL: [
            CallbackQueryHandler(handle_category_decision, pattern="^(accept|choose_other)_category$"),
            CallbackQueryHandler(manual_category_select, pattern="^manual_cat_"),
            CallbackQueryHandler(handle_category_decision, pattern="^cancel_action$")
        ],
    },
    fallbacks=[CommandHandler("cancel", handle_category_decision)]
)

def register_handlers(application):
    application.add_handler(category_conv)
