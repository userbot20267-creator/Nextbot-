# features/weekly_report/reporter.py
from telegram import Bot
from telegram.constants import ParseMode
from config import ADMIN_ID
from .services import get_weekly_stats

async def send_weekly_report(bot: Bot):
    """تنسيق وإرسال التقرير الأسبوعي للمالك"""
    stats = get_weekly_stats()
    
    # تنسيق التاريخ
    week_start = stats["week_ago"].strftime("%Y-%m-%d")
    week_end = stats["today"].strftime("%Y-%m-%d")
    
    text = f"📊 *التقرير الأسبوعي للبوت*\n📅 {week_start} → {week_end}\n\n"
    
    text += f"👥 *المستخدمون:*\n"
    text += f"• الجدد هذا الأسبوع: {stats['new_users']}\n"
    text += f"• إجمالي المستخدمين: {stats['total_users']}\n\n"
    
    text += f"📚 *الكتب:*\n"
    text += f"• تحميلات هذا الأسبوع: {stats['weekly_downloads']}\n"
    text += f"• إجمالي الكتب: {stats['total_books']}\n\n"
    
    if stats["top_books"]:
        text += "📈 *أكثر الكتب تحميلاً:*\n"
        for i, (title, count) in enumerate(stats["top_books"], 1):
            text += f"{i}. {title} - {count} تحميل\n"
    
    if stats["top_categories"]:
        text += "\n📁 *أكثر الأقسام نشاطاً:*\n"
        for i, (name, count) in enumerate(stats["top_categories"], 1):
            text += f"{i}. {name} - {count} تحميل\n"
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"خطأ في إرسال التقرير الأسبوعي: {e}")
