# services/auto_publisher.py

from telegram import Bot
from telegram.constants import ParseMode
import database as db


async def publish_book_to_channel(
    bot: Bot,
    title: str,
    author: str,
    file_id: str = None,
    file_link: str = None,
    cover_url: str = None
) -> bool:
    """
    نشر كتاب جديد في القناة المحددة.
    يرجع True إذا نجح النشر.
    """
    channel_id = db.get_channel_id()
    if not channel_id:
        return False

    caption = (
        f"📖 *{title}*\n"
        f"✍️ {author}\n\n"
        f"📚 *مكتبة البوت الذكية*"
    )

    try:
        if cover_url:
            # إرسال صورة الغلاف مع الكابشن
            await bot.send_photo(
                chat_id=channel_id,
                photo=cover_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
            # إذا كان هناك ملف، نرسله بعد الصورة
            if file_id:
                await bot.send_document(
                    chat_id=channel_id,
                    document=file_id,
                    caption=f"📥 *تحميل:* {title}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif file_link:
                await bot.send_message(
                    chat_id=channel_id,
                    text=f"🔗 *رابط الكتاب:* {file_link}",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            # لا يوجد غلاف
            if file_id:
                await bot.send_document(
                    chat_id=channel_id,
                    document=file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                caption += f"\n\n🔗 {file_link}"
                await bot.send_message(
                    chat_id=channel_id,
                    text=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
        return True
    except Exception as e:
        print(f"خطأ في النشر للقناة: {e}")
        return False
