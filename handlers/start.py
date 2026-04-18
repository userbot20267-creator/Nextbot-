# handlers/start.py

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards import main_menu, subscription_required_keyboard
from utils import check_user_subscription, get_required_channels_from_db


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /start - تسجيل المستخدم وفحص الاشتراك الإجباري مع دعم الإحالة"""
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""

    # إضافة المستخدم إلى قاعدة البيانات
    db.add_user(user_id, username, first_name, last_name)

    # --- معالجة الإحالة إذا وجدت ---
    args = context.args
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0][4:])
            if referrer_id != user_id:
                # استيراد دالة معالجة الإحالة من ميزة referral
                from features.referral.services import process_referral
                success = process_referral(user_id, referrer_id)
                if success:
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text="🎉 *مبروك!* انضم مستخدم جديد عبر رابط الإحالة الخاص بك وحصلت على 50 نقطة!",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass  # تجاهل إذا فشل إرسال الإشعار (مثلاً المستخدم حظر البوت)
        except ValueError:
            pass  # معرف غير صالح، تجاهل
    # --- معالجة الرابط العميق للكتاب ---
    book_id_to_send = None
    if args:
        for arg in args:
            if arg.startswith("book_"):
                try:
                    book_id_to_send = int(arg[5:])
                    break
                except ValueError:
                    pass

    # --- فحص الاشتراك الإجباري ---
    is_subscribed, _ = await check_user_subscription(context.bot, user_id)

    if not is_subscribed:
        channels = await get_required_channels_from_db()
        await update.message.reply_text(
            "⚠️ *يجب عليك الاشتراك في القنوات التالية أولاً لاستخدام البوت:*\n\n"
            "بعد الاشتراك اضغط على زر *'تحققت من الاشتراك'*",
            reply_markup=subscription_required_keyboard(channels),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # --- رسالة الترحيب للمستخدم المشترك ---
    await update.message.reply_text(
        f"👋 *أهلاً بك {first_name} في مكتبة البوت الذكية!*\n\n"
        "يمكنك تصفح الأقسام، البحث عن كتاب، أو استكشاف آلاف الكتب.",
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يتم استدعاؤه عند ضغط المستخدم على 'تحققت من الاشتراك'"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    is_subscribed, _ = await check_user_subscription(context.bot, user_id)

    if is_subscribed:
        db.update_activity(user_id)
        await query.edit_message_text(
            f"✅ *تم التحقق من اشتراكك بنجاح!*\n\n"
            f"أهلاً بك في مكتبة البوت الذكية.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        channels = await get_required_channels_from_db()
        await query.edit_message_text(
            "❌ *لم يتم اكتشاف اشتراكك في جميع القنوات بعد.*\n\n"
            "تأكد من الانضمام ثم اضغط الزر مرة أخرى.",
            reply_markup=subscription_required_keyboard(channels),
            parse_mode=ParseMode.MARKDOWN
        )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """زر 'حول البوت'"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 *مكتبة البوت الذكية*\n\n"
        "• تصفح آلاف الكتب حسب الأقسام والمؤلفين.\n"
        "• بحث ذكي داخل المكتبة وخارجها.\n"
        "• حفظ تلقائي للكتب الجديدة.\n\n"
        "👨‍💻 *للمالك:* لوحة تحكم متكاملة عبر /admin",
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """زر العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    await query.edit_message_text(
        f"👋 *أهلاً بك {user.first_name}*\n\nاختر ما تريد القيام به:",
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )


start_handler = CommandHandler("start", start)

callback_handlers = [
    CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"),
    CallbackQueryHandler(about, pattern="^about$"),
    CallbackQueryHandler(back_to_main, pattern="^back_main$"),
    ]
