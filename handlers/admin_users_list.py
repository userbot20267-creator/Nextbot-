from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection
from config import ADMIN_ID

async def list_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ عذراً، هذا الأمر مخصص للمالك فقط.")
        return

    await query.answer("🔄 جاري تحميل قائمة المستخدمين... ⏳")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # استخدام first_name بدلاً من full_name
            # إذا كان لديك last_name أيضاً، يمكن دمجها هكذا:
            # CONCAT(first_name, ' ', COALESCE(last_name, '')) AS full_name
            cur.execute("""
                SELECT user_id, username, first_name, 
                       COALESCE(last_name, '') as last_name 
                FROM users 
                ORDER BY joined_at DESC 
                LIMIT 50
            """)
            users = cur.fetchall()
            
    if not users:
        await query.message.reply_text("⚠️ لا يوجد مستخدمون مسجلون حالياً.")
        return

    text = "👥 **قائمة آخر 50 مستخدماً:**\n\n"
    for user in users:
        username = f"@{user['username']}" if user['username'] else "بدون يوزر"
        # دمج الاسم الأول والأخير
        full_name = f"{user['first_name']} {user['last_name']}".strip()
        if not full_name:
            full_name = "بدون اسم"
        text += f"👤 {full_name} ({username}) - `{user['user_id']}`\n"
    
    await query.message.reply_text(text, parse_mode="Markdown")

# Register handler in main.py:
# application.add_handler(CallbackQueryHandler(list_all_users, pattern="^admin_users_list$"))
