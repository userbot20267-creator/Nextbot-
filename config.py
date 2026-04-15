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
