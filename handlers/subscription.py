# handlers/subscription.py

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards import subscription_required_keyboard, main_menu
from utils import check_user_subscription, get_required_channels_from_db


async def require_subscription_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    دالة مساعدة للتحقق من الاشتراك أثناء أي تفاعل.
    إذا لم يكن المستخدم مشتركًا، تعدل الواجهة لعرض قنوات الاشتراك وترجع False.
    يمكن استخدامها من داخل أي handler قبل تنفيذ الإجراء.
    
    مثال:
        if not await require_subscription_interactive(update, context):
            return
    """
    user_id = update.effective_user.id
    is_subscribed, not_joined = await check_user_subscription(context.bot, user_id)

    if is_subscribed:
        # تحديث آخر نشاط إذا كان مشتركًا (يدل على تفاعل نشط)
        db.update_activity(user_id)
        return True

    # المستخدم غير مشترك
    channels = await get_required_channels_from_db()
    keyboard = subscription_required_keyboard(channels)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "⚠️ *يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:*\n\n"
            "بعد الاشتراك، اضغط على زر *'تحققت من الاشتراك'*.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        # في حال كان الأمر عبر رسالة نصية وليس callback
        await update.message.reply_text(
            "⚠️ *يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:*\n\n"
            "بعد الاشتراك، اضغط على زر *'تحققت من الاشتراك'*.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
    return False


async def subscription_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يتم استدعاؤه عندما يضغط المستخدم على زر "تحققت من الاشتراك".
    يعيد التحقق من العضوية ويحدث الواجهة وفقًا لذلك.
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    is_subscribed, _ = await check_user_subscription(context.bot, user_id)

    if is_subscribed:
        db.update_activity(user_id)
        await query.edit_message_text(
            "✅ *تم التحقق من اشتراكك بنجاح!*\n\n"
            "مرحبًا بك في مكتبة البوت الذكية.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        channels = await get_required_channels_from_db()
        keyboard = subscription_required_keyboard(channels)
        await query.edit_message_text(
            "❌ *لم يتم اكتشاف اشتراكك في جميع القنوات بعد.*\n\n"
            "تأكد من الانضمام إلى جميع القنوات المطلوبة ثم اضغط الزر مرة أخرى.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )


async def force_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    أمر /check للتحقق من الاشتراك بشكل يدوي (اختياري).
    """
    user_id = update.effective_user.id
    is_subscribed, not_joined = await check_user_subscription(context.bot, user_id)

    if is_subscribed:
        db.update_activity(user_id)
        await update.message.reply_text(
            "✅ أنت مشترك في جميع القنوات المطلوبة.",
            reply_markup=main_menu()
        )
    else:
        channels = await get_required_channels_from_db()
        keyboard = subscription_required_keyboard(channels)
        await update.message.reply_text(
            f"❌ لم تشترك بعد في {len(not_joined)} من القنوات المطلوبة:\n"
            + "\n".join(not_joined),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )


# تجميع الـ handlers الخاصة بالاشتراك (للتسجيل في main.py)
subscription_handlers = [
    CallbackQueryHandler(subscription_check_callback, pattern="^check_subscription$"),
]
