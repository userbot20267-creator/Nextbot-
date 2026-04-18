# features/referral/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from .services import generate_referral_link, process_referral, get_referral_stats
import database as db

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /referral - يعرض رابط الإحالة الخاص بالمستخدم وإحصائياته.
    """
    user = update.effective_user
    user_id = user.id
    
    # التأكد من وجود المستخدم في قاعدة البيانات
    db.add_user(user_id, user.username, user.first_name, user.last_name or "")
    
    link = generate_referral_link(user_id)
    stats = get_referral_stats(user_id)
    
    text = (
        "🎁 *نظام الإحالة*\n\n"
        f"🔗 *رابط الإحالة الخاص بك:*\n`{link}`\n\n"
        f"👥 *عدد من انضموا عبر رابطك:* {stats['count']}\n"
        f"🏆 *النقاط المكتسبة من الإحالات:* {stats['points_earned']}\n\n"
        "💡 *شارك رابطك مع أصدقائك، وعند انضمامهم ستحصل على 50 نقطة!*"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}&text=انضم%20إلى%20مكتبة%20البوت%20الذكية%20واحصل%20على%20آلاف%20الكتب%20المجانية!")]
    ])
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def handle_start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    تعالج بدء البوت برابط إحالة: /start ref_123456
    يتم استدعاؤها من start.py أو تعديل start_handler.
    """
    args = context.args
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0][4:])
            new_user = update.effective_user
            new_user_id = new_user.id
            
            # إضافة المستخدم الجديد
            db.add_user(new_user_id, new_user.username, new_user.first_name, new_user.last_name or "")
            
            # معالجة الإحالة
            success = process_referral(new_user_id, referrer_id)
            
            if success:
                # إرسال إشعار للمُحيل
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 *مبروك!* انضم مستخدم جديد عبر رابط الإحالة الخاص بك وحصلت على 50 نقطة!"
                    )
                except:
                    pass
        except ValueError:
            pass

def register_handlers(application):
    """
    تسجيل معالجات نظام الإحالة.
    """
    application.add_handler(CommandHandler("referral", referral_command))
    # ملاحظة: معالجة /start ref_xxx يجب دمجها مع start_handler الموجود
