# handlers/user.py

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from datetime import datetime

import database as db
from keyboards import main_menu, cancel_only_keyboard
from config import ADMIN_ID

# حالات المحادثة للاقتراحات
WAITING_FEEDBACK = 1


# ---------- أوامر المستخدم العادي ----------
async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض معلومات الحساب وإحصائيات الاستخدام"""
    user = update.effective_user
    user_id = user.id

    # جلب إحصائيات من قاعدة البيانات (يجب إضافة الدوال لاحقاً)
    joined_date = db.get_user_joined_date(user_id)
    downloads_count = db.get_user_downloads_count(user_id)
    is_banned = db.is_user_banned(user_id)

    text = (
        f"👤 *معلومات حسابك*\n\n"
        f"🆔 المعرف: `{user_id}`\n"
        f"📅 تاريخ الانضمام: {joined_date.strftime('%Y-%m-%d') if joined_date else 'غير معروف'}\n"
        f"📚 عدد الكتب المحملة: {downloads_count}\n"
        f"🚫 حالة الحظر: {'محظور' if is_banned else 'نشط'}\n"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة الأوامر وطريقة الاستخدام"""
    text = (
        "🤖 *مرحباً بك في مكتبة البوت الذكية*\n\n"
        "📌 *الأوامر المتاحة:*\n"
        "/start - بدء استخدام البوت\n"
        "/me - عرض معلومات حسابك\n"
        "/help - عرض هذه المساعدة\n"
        "/feedback - إرسال اقتراح أو مشكلة\n\n"
        "📚 *طريقة التصفح:*\n"
        "• اضغط 'تصفح الأقسام' ثم اختر القسم ← المؤلف ← الكتاب\n"
        "• يمكنك تحميل الكتب المتاحة مباشرة\n\n"
        "🔍 *البحث:*\n"
        "• اضغط 'بحث عن كتاب' وأرسل اسم الكتاب + المؤلف\n"
        "• البوت يبحث في المكتبة ثم في المصادر الخارجية\n\n"
        "⚠️ *الاشتراك الإجباري:*\n"
        "• يجب الانضمام للقنوات المطلوبة قبل الاستخدام\n"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())


async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إرسال اقتراح أو مشكلة"""
    await update.message.reply_text(
        "📝 *أرسل رسالتك التي تريد إيصالها للإدارة:*\n\n"
        "يمكنك كتابة اقتراح، مشكلة، أو طلب كتاب معين.\n"
        "أرسل /cancel للإلغاء.",
        reply_markup=cancel_only_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_FEEDBACK


async def feedback_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استلام الرسالة وإرسالها للمالك"""
    user = update.effective_user
    message_text = update.message.text or update.message.caption or ""

    if not message_text:
        await update.message.reply_text("❌ يرجى إرسال نص.")
        return WAITING_FEEDBACK

    # إعداد رسالة للمالك
    admin_message = (
        f"📬 *رسالة جديدة من مستخدم*\n\n"
        f"👤 *المرسل:* {user.full_name} (@{user.username or 'بدون معرف'})\n"
        f"🆔 *ID:* `{user.id}`\n\n"
        f"📝 *الرسالة:*\n{message_text}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text(
            "✅ *تم إرسال رسالتك بنجاح.*\nشكراً لتواصلك معنا!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إرسال الرسالة. يرجى المحاولة لاحقاً.",
            reply_markup=main_menu()
        )
        print(f"خطأ في إرسال feedback: {e}")

    return ConversationHandler.END


async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء عملية feedback"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu())
    else:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu())
    return ConversationHandler.END


# ---------- معالجة الأخطاء العامة للمستخدم ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج أخطاء عام (يمكن تسجيله في main.py)"""
    print(f"حدث خطأ: {context.error}")
    # يمكن إرسال تنبيه للمطور
    if update and update.effective_user:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ خطأ في البوت:\n{context.error}\n\nمن المستخدم: {update.effective_user.id}"
        )


# ---------- تجميع الـ Handlers ----------
user_command_handlers = [
    CommandHandler("me", me_command),
    CommandHandler("help", help_command),
]

feedback_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("feedback", feedback_start)],
    states={
        WAITING_FEEDBACK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_receive)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_feedback),
        CallbackQueryHandler(cancel_feedback, pattern="^cancel_action$"),
    ],
)

# إذا أردت إضافة زر "حول البوت" من القائمة الرئيسية، تمت معالجته في start.py
