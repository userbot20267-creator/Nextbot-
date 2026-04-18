# features/referral/services.py
import database as db
from config import BOT_USERNAME  # ستحتاج إضافة BOT_USERNAME في config.py

def generate_referral_link(user_id: int) -> str:
    """
    توليد رابط إحالة فريد للمستخدم.
    مثال: https://t.me/YourBot?start=ref_123456
    """
    if not BOT_USERNAME:
        return "❌ لم يتم ضبط معرف البوت في config.py"
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

def process_referral(new_user_id: int, referrer_id: int) -> bool:
    """
    معالجة عملية الإحالة عند انضمام مستخدم جديد عبر رابط إحالة.
    - يسجل الإحالة في جدول referrals
    - يمنح المُحيل نقاطاً (مثلاً 50 نقطة)
    - (اختياري) يمنح المستخدم الجديد نقاطاً ترحيبية
    """
    if referrer_id == new_user_id:
        return False  # لا يمكن للمستخدم إحالة نفسه
    
    # التحقق من أن المُحيل موجود
    referrer = db.get_user_joined_date(referrer_id)
    if not referrer:
        return False
    
    # التحقق من عدم وجود إحالة مسبقة لهذا المستخدم
    if db.get_user_referrer(new_user_id):
        return False
    
    try:
        # 1. تسجيل الإحالة في جدول referrals
        db.add_referral(referrer_id, new_user_id)
        
        # 2. تحديث عمود referred_by في جدول users
        db.set_user_referrer(new_user_id, referrer_id)
        
        # 3. منح المُحيل نقاطاً
        db.add_user_points(referrer_id, 50)  # 50 نقطة مكافأة
        
        # 4. (اختياري) منح المستخدم الجديد نقاطاً ترحيبية
        db.add_user_points(new_user_id, 10)
        
        return True
    except Exception as e:
        print(f"خطأ في معالجة الإحالة: {e}")
        return False

def get_referral_stats(user_id: int) -> dict:
    """
    جلب إحصائيات الإحالة لمستخدم معين.
    """
    referrals = db.get_user_referrals(user_id)
    return {
        "count": len(referrals),
        "points_earned": len(referrals) * 50,
        "referrals": referrals[:10]  # آخر 10
    }
