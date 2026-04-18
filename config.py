# config.py
import os
from dotenv import load_dotenv

# تحميل ملف .env في بيئة التطوير المحلية
load_dotenv()

# توكن البوت من BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود في المتغيرات البيئية")

# معرف المالك (رقم حسابه في تليجرام)
ADMIN_ID = os.getenv("ADMIN_ID")
if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        raise ValueError("ADMIN_ID يجب أن يكون رقماً صحيحاً")
else:
    raise ValueError("ADMIN_ID غير موجود في المتغيرات البيئية")

# رابط قاعدة البيانات PostgreSQL (للاستضافة على Render)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL غير موجود في المتغيرات البيئية")

# (اختياري) إعدادات إضافية
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
# مفتاح OpenRouter API لتلخيص الكتب بالذكاء الاصطناعي
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    # لا نرفع خطأ هنا حتى لا يتوقف البوت إذا لم تكن الخاصية مفعلة
    # لكن بعض الميزات (مثل التلخيص) لن تعمل
    print("⚠️ تحذير: OPENROUTER_API_KEY غير موجود. ميزة تلخيص الكتب معطلة.")
# اسم مستخدم البوت (لنظام الإحالة والروابط العميقة)
BOT_USERNAME = os.getenv("BOT_USERNAME")
if not BOT_USERNAME:
    print("⚠️ تحذير: BOT_USERNAME غير موجود. ميزة الإحالة والروابط العميقة لن تعمل.")
