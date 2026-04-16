from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import get_connection

async def show_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT points FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            
            # Get rank (leaderboard position)
            cur.execute("SELECT COUNT(*) + 1 FROM users WHERE points > (SELECT points FROM users WHERE user_id = %s)", (user_id,))
            rank = cur.fetchone()[0]
            
    points = user['points'] if user else 0
    
    text = (
        f"🏆 **لوحة الشرف الشخصية:**\n\n"
        f"💰 رصيد نقاطك: `{points}` نقطة\n"
        f"🎖️ ترتيبك الحالي: `{rank}`\n\n"
        "💡 يمكنك زيادة نقاطك من خلال تحميل الكتب وتقييمها باستمرار!"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def add_points(user_id: int, points: int = 1):
    """Utility function to add points to a user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (points, user_id))
            conn.commit()

# Register handler in main.py:
# application.add_handler(CommandHandler("points", show_points))
# application.add_handler(CommandHandler("me", show_points))
