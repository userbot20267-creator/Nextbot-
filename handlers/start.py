# handlers/start.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards import main_menu, subscription_required_keyboard
from utils import check_user_subscription, get_required_channels_from_db

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /start - تسجيل المستخدم وفحص الاشتراك الإجباري"""
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    
    # حفظ أو تحديث بيانات المستخدم في قاعدة البيانات
    db.add_user(user_id, username, first_name, last_name)
    
    # فحص الاشتراك في القنوات الإجبارية
    is_subscribed, not_joined = await check_user_subscription(context.bot, user_id)
    
    if not is_subscribed:
        channels = await get_required_channels_from_db()
        await update.message.reply_text(
            "⚠️ *يجب عليك الاشتراك في القنوات التالية أولاً لاستخدام البوت:*\n\n"
            "بعد الاشتراك اضغط على زر *'تحققت من الاشتراك'*",
            reply_markup=subscription_required_keyboard(channels),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # إذا كان مشتركاً بالفعل نعرض القائمة الرئيسية
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
        # تحديث نشاط المستخدم بعد الاشتراك الناجح
        db.update_activity(user_id)
        await query.edit_message_text(
            f"✅ *تم التحقق من اشتراكك بنجاح!*\n\n"
            f"أهلاً بك في مكتبة البوت الذكية.",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # إعادة إظهار رسالة الاشتراك مع القنوات
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

# إنشاء الـ Handler الخاص بـ start
start_handler = CommandHandler("start", start)

# Handlers للأزرار العامة (يتم تسجيلها في main.py)
# لكننا سنعرضها هنا كمرجع
callback_handlers = [
    CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"),
    CallbackQueryHandler(about, pattern="^about$"),
    CallbackQueryHandler(back_to_main, pattern="^back_main$"),
  ]
