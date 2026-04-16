import csv
import io
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_connection
from config import ADMIN_ID

async def export_users_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ عذراً، هذا الأمر مخصص للمالك فقط.")
        return

    await query.answer("🔄 جاري تحضير ملف CSV... يرجى الانتظار. ⏳")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username, full_name, points, joined_at FROM users")
            users = cur.fetchall()
            
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'Username', 'Full Name', 'Points', 'Joined At'])
    for user in users:
        writer.writerow([user['user_id'], user['username'], user['full_name'], user['points'], user['joined_at']])
    
    output.seek(0)
    
    # Send CSV file
    await query.message.reply_document(
        document=io.BytesIO(output.getvalue().encode('utf-8')),
        filename="users_report.csv",
        caption="📊 **تقرير المستخدمين الكامل** (بصيغة CSV)"
    )

# Register handler in main.py:
# application.add_handler(CallbackQueryHandler(export_users_csv, pattern="^admin_export_users$"))
