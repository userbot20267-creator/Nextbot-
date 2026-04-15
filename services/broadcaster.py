# services/broadcaster.py

import asyncio
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError, Forbidden, RetryAfter
import database as db


# ---------- الإذاعة الأساسية ----------
async def broadcast_message(
    bot: Bot,
    message_text: str,
    parse_mode: str = "HTML",
    user_ids: Optional[List[int]] = None,
    disable_web_page_preview: bool = False,
    reply_markup: Optional[Any] = None,
    delay: float = 0.05
) -> Tuple[int, int, List[int]]:
    """
    إرسال رسالة إلى مجموعة من المستخدمين.
    
    Args:
        bot: نسخة البوت
        message_text: نص الرسالة
        parse_mode: صيغة النص (HTML, Markdown, MarkdownV2)
        user_ids: قائمة معرفات المستخدمين (إذا كان None، يجلب جميع المستخدمين النشطين)
        disable_web_page_preview: تعطيل معاينة الروابط
        reply_markup: أزرار تفاعلية (اختياري)
        delay: تأخير بين الإرسالات لتجنب حدود المعدل
    
    Returns:
        (عدد الناجح, عدد الفاشل, قائمة معرفات المستخدمين المحظورين للبوت)
    """
    if user_ids is None:
        user_ids = db.get_all_users()  # جميع المستخدمين غير المحظورين
    
    success = 0
    failed = 0
    blocked_users = []
    
    for i, user_id in enumerate(user_ids):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                reply_markup=reply_markup
            )
            success += 1
            
            # تأخير بسيط لتجنب تجاوز حدود تليجرام (30 رسالة/ثانية)
            if delay > 0:
                await asyncio.sleep(delay)
                
        except Forbidden:
            # المستخدم حظر البوت
            failed += 1
            blocked_users.append(user_id)
            # يمكن تحديث قاعدة البيانات لوضع علامة محظور (اختياري)
            # db.mark_user_blocked(user_id)
            
        except RetryAfter as e:
            # تليجرام يطلب الانتظار
            wait_time = e.retry_after
            print(f"⚠️ تم طلب الانتظار {wait_time} ثانية")
            await asyncio.sleep(wait_time)
            # إعادة محاولة الإرسال
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview,
                    reply_markup=reply_markup
                )
                success += 1
            except Exception:
                failed += 1
                
        except TelegramError as e:
            print(f"❌ خطأ تليجرام مع المستخدم {user_id}: {e}")
            failed += 1
            
        except Exception as e:
            print(f"❌ خطأ غير متوقع مع المستخدم {user_id}: {e}")
            failed += 1
        
        # تحديث التقدم كل 50 مستخدم (اختياري)
        if (i + 1) % 50 == 0:
            print(f"📊 تقدم الإذاعة: {i+1}/{len(user_ids)} (نجاح: {success}, فشل: {failed})")
    
    return success, failed, blocked_users


# ---------- إذاعة لجميع المستخدمين ----------
async def broadcast_to_users(
    bot: Bot,
    text: str,
    parse_mode: str = "HTML",
    exclude_blocked: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    إذاعة رسالة لجميع المستخدمين المسجلين.
    
    Args:
        bot: نسخة البوت
        text: نص الرسالة
        parse_mode: صيغة التنسيق
        exclude_blocked: استبعاد المستخدمين المحظورين
        **kwargs: معاملات إضافية لـ send_message
    
    Returns:
        قاموس يحتوي على إحصائيات الإذاعة
    """
    # جلب المستخدمين
    if exclude_blocked:
        user_ids = db.get_all_users()  # دالة ترجع غير المحظورين فقط
    else:
        # جلب الجميع (يمكن إضافة دالة في database)
        user_ids = db.get_all_users(include_banned=True)
    
    start_time = datetime.now()
    success, failed, blocked = await broadcast_message(
        bot=bot,
        message_text=text,
        parse_mode=parse_mode,
        user_ids=user_ids,
        **kwargs
    )
    end_time = datetime.now()
    
    # تنظيف المستخدمين المحظورين (اختياري)
    if blocked:
        for user_id in blocked:
            db.ban_user(user_id)  # نضعهم كمحظورين تلقائياً
    
    return {
        "total_users": len(user_ids),
        "success_count": success,
        "failed_count": failed,
        "blocked_count": len(blocked),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "start_time": start_time,
        "end_time": end_time,
    }


# ---------- إذاعة مع مرفق ----------
async def broadcast_document(
    bot: Bot,
    document: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    user_ids: Optional[List[int]] = None,
    **kwargs
) -> Tuple[int, int]:
    """
    إرسال ملف (مستند) إلى مجموعة من المستخدمين.
    
    Args:
        bot: نسخة البوت
        document: file_id أو URL للملف
        caption: نص توضيحي للملف
        parse_mode: صيغة النص للـ caption
        user_ids: قائمة معرفات المستخدمين
    
    Returns:
        (عدد الناجح, عدد الفاشل)
    """
    if user_ids is None:
        user_ids = db.get_all_users()
    
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_document(
                chat_id=user_id,
                document=document,
                caption=caption,
                parse_mode=parse_mode,
                **kwargs
            )
            success += 1
            await asyncio.sleep(0.05)
        except Forbidden:
            failed += 1
            db.ban_user(user_id)
        except Exception:
            failed += 1
    
    return success, failed


# ---------- إذاعة صورة ----------
async def broadcast_photo(
    bot: Bot,
    photo: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    user_ids: Optional[List[int]] = None,
    **kwargs
) -> Tuple[int, int]:
    """
    إرسال صورة إلى مجموعة من المستخدمين.
    
    Args:
        bot: نسخة البوت
        photo: file_id أو URL للصورة
        caption: نص توضيحي
        parse_mode: صيغة النص
        user_ids: قائمة معرفات المستخدمين
    
    Returns:
        (عدد الناجح, عدد الفاشل)
    """
    if user_ids is None:
        user_ids = db.get_all_users()
    
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
                **kwargs
            )
            success += 1
            await asyncio.sleep(0.05)
        except Forbidden:
            failed += 1
            db.ban_user(user_id)
        except Exception:
            failed += 1
    
    return success, failed


# ---------- الحصول على إحصائيات الإذاعة ----------
def get_broadcast_stats() -> Dict[str, Any]:
    """
    الحصول على إحصائيات المستخدمين للإذاعة.
    
    Returns:
        قاموس يحتوي على عدد المستخدمين النشطين، المحظورين، إلخ.
    """
    total_users = db.count_users()
    active_today = db.count_active_today()
    banned_users = db.count_banned_users() if hasattr(db, 'count_banned_users') else 0
    
    return {
        "total_users": total_users,
        "active_today": active_today,
        "banned_users": banned_users,
        "eligible_for_broadcast": total_users - banned_users,
        "timestamp": datetime.now().isoformat()
    }


# ---------- إذاعة متقدمة مع دعم الأزرار ----------
async def broadcast_with_keyboard(
    bot: Bot,
    text: str,
    reply_markup: Any,
    parse_mode: str = "HTML",
    user_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    إذاعة رسالة مع أزرار تفاعلية.
    
    Args:
        bot: نسخة البوت
        text: نص الرسالة
        reply_markup: InlineKeyboardMarkup أو ReplyKeyboardMarkup
        parse_mode: صيغة التنسيق
        user_ids: قائمة معرفات المستخدمين
    
    Returns:
        قاموس بالإحصائيات
    """
    if user_ids is None:
        user_ids = db.get_all_users()
    
    start_time = datetime.now()
    success, failed, blocked = await broadcast_message(
        bot=bot,
        message_text=text,
        parse_mode=parse_mode,
        user_ids=user_ids,
        reply_markup=reply_markup
    )
    end_time = datetime.now()
    
    return {
        "total_users": len(user_ids),
        "success_count": success,
        "failed_count": failed,
        "blocked_count": len(blocked),
        "duration_seconds": (end_time - start_time).total_seconds(),
    }


# ---------- اختبار الإذاعة على المستخدم الحالي ----------
async def test_broadcast(bot: Bot, user_id: int, **kwargs) -> bool:
    """
    إرسال اختبار للمستخدم الحالي قبل الإذاعة الشاملة.
    
    Args:
        bot: نسخة البوت
        user_id: معرف المستخدم (عادةً المالك)
        **kwargs: نفس معاملات broadcast_message
    
    Returns:
        True إذا نجح الإرسال، False إذا فشل
    """
    try:
        await bot.send_message(chat_id=user_id, **kwargs)
        return True
    except Exception as e:
        print(f"فشل اختبار الإذاعة: {e}")
        return False
