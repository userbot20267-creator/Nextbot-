from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import get_connection
from keyboards import main_menu

async def show_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # تحديد ما إذا كان التحديث من رسالة أو استدعاء زر
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        is_callback = True
    else:
        is_callback = False

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. جلب نقاط المستخدم
            cur.execute("SELECT points FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

            if user is None:
                # المستخدم غير موجود في جدول النقاط
                points = 0
                rank = "غير مصنف"
            else:
                points = user['points']
                # 2. حساب الترتيب: عدد المستخدمين الذين لديهم نقاط أكبر + 1
                cur.execute("SELECT COUNT(*) + 1 as rank FROM users WHERE points > %s", (points,))
                row = cur.fetchone()
                rank = row['rank'] if row else "غير مصنف"

    text = (
        f"🏆 **لوحة الشرف الشخصية:**\n\n"
        f"💰 رصيد نقاطك: `{points}` نقطة\n"
        f"🎖️ ترتيبك الحالي: `{rank}`\n\n"
        "💡 يمكنك زيادة نقاطك من خلال تحميل الكتب وتقييمها باستمرار!"
    )

    if is_callback:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())

async def add_points(user_id: int, points: int = 1):
    """زيادة نقاط المستخدم."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (points, user_id))
            conn.commit()

# تسجيل المعالج في main.py:
# application.add_handler(CommandHandler("points", show_points))
# application.add_handler(CommandHandler("me", show_points))
