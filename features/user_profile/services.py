# features/user_profile/services.py
import database as db


def get_user_stats(user_id: int) -> dict:
    """
    جلب إحصائيات المستخدم الكاملة للملف الشخصي.
    
    Returns:
        قاموس يحتوي على:
        - user_id: معرف المستخدم
        - downloads: عدد التحميلات
        - points: النقاط
        - favorites: عدد المفضلة
        - joined: تاريخ الانضمام
        - badges: قائمة الشارات
    """
    stats = {
        "user_id": user_id,
        "downloads": db.get_user_downloads_count(user_id),
        "points": db.get_user_points(user_id),
        "favorites": len(db.get_user_favorites(user_id)),
        "joined": db.get_user_joined_date(user_id),
        "badges": []
    }
    
    # تحديد الشارات بناءً على عدد التحميلات
    downloads = stats["downloads"]
    if downloads >= 50:
        stats["badges"].append("🏆 قارئ نهم")
    elif downloads >= 20:
        stats["badges"].append("📚 قارئ متقدم")
    elif downloads >= 5:
        stats["badges"].append("📖 قارئ مبتدئ")
    
    # شارة إضافية للنقاط
    if stats["points"] >= 500:
        stats["badges"].append("⭐ نجم المكتبة")
    
    # شارة للمفضلة
    if stats["favorites"] >= 10:
        stats["badges"].append("❤️ جامع الكتب")
    
    return stats
