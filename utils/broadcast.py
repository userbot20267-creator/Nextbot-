# utils/broadcast.py

import asyncio
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from database import get_all_users

async def broadcast_message(bot: Bot, message_text: str, parse_mode: str = "HTML") -> tuple[int, int]:
    """
    إرسال رسالة إلى جميع المستخدمين المسجلين.
    ترجع (عدد الناجح, عدد الفاشل).
    """
    user_ids = get_all_users()  # ترجع قائمة بالأرقام
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message_text, parse_mode=parse_mode)
            success += 1
            # تأخير بسيط لتجنب حدود المعدل (Rate Limits)
            await asyncio.sleep(0.05)
        except Forbidden:
            # المستخدم حظر البوت
            failed += 1
        except TelegramError as e:
            print(f"خطأ في إرسال إلى {user_id}: {e}")
            failed += 1
    
    return success, failed
