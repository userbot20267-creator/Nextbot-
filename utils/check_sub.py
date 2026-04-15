# utils/check_sub.py

from telegram import Bot, InlineKeyboardMarkup
from telegram.error import TelegramError
from database import get_required_channels

async def get_required_channels_from_db():
    """جلب قائمة معرفات القنوات الإجبارية من قاعدة البيانات"""
    return get_required_channels()  # ترجع قائمة نصوص مثل ['@channel1', '-100123456']

async def check_user_subscription(bot: Bot, user_id: int) -> tuple[bool, list]:
    """
    فحص اشتراك المستخدم في جميع القنوات الإجبارية.
    ترجع (منضم لكل القنوات, قائمة القنوات غير المنضم لها)
    """
    channels = await get_required_channels_from_db()
    not_joined = []
    
    for channel in channels:
        try:
            # استخدام get_chat_member لفحص العضوية
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            # الحالات التي تعتبر غير منضم: left, kicked, restricted
            if member.status in ['left', 'kicked', 'restricted']:
                not_joined.append(channel)
        except TelegramError:
            # إذا حدث خطأ (مثل قناة خاصة غير موجودة) نفترض أنه غير منضم
            not_joined.append(channel)
    
    return (len(not_joined) == 0, not_joined)
