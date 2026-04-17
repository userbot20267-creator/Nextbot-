# handlers/admin_download.py
"""
معالج منفصل لتنزيل الكتب الخارجية للمالك دون تعديل admin.py
يتمتع بأولوية أعلى لاعتراض أحداث add_search_result
"""

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import database as db
from services.scraper import download_file_to_telegram
from keyboards import admin_panel_keyboard
from config import ADMIN_ID


def ensure_uncategorized_category() -> int:
    """يتأكد من وجود قسم 'غير مصنف' ويعيد معرفه"""
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    db.add_category("غير مصنف")
    categories = db.get_all_categories()
    for cat_id, name in categories:
        if name == "غير مصنف":
            return cat_id
    return 1


async def admin_download_and_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    تلتقط أحداث add_search_result من لوحة تحكم المالك،
    تقوم بتنزيل الملف ورفعه وحفظه في قاعدة البيانات، ثم تمنع الانتشار.
    """
    query = update.callback_query

    # التحقق من أن المستخدم هو المالك
    if query.from_user.id != ADMIN_ID:
        return

    # نتعامل فقط مع الحدث add_search_result
    if query.data != "add_search_result":
        return

    # نمنع المعالجات الأخرى من الرد على نفس الحدث
    await query.answer("⏳ جارٍ تنزيل الكتاب...")

    # استخراج معلومات الكتاب من context.user_data (المحفوظة بواسطة admin.py)
    results = context.user_data.get("search_results", [])
    index = context.user_data.get("result_index", 0)

    if not results or index >= len(results):
        await query.edit_message_text("❌ انتهت صلاحية البحث. أعد المحاولة.")
        return

    title, author, link = results[index]

    await query.edit_message_text(
        f"⏳ *جاري تنزيل:* {title}\nمن فضلك انتظر...",
        parse_mode=ParseMode.MARKDOWN
    )

    # تنزيل الملف ورفعه إلى تليجرام
    file_id = await download_file_to_telegram(context.bot, link, update.effective_user.id)

    if not file_id:
        await query.edit_message_text(
            "❌ *فشل تنزيل الكتاب.*\nقد يكون الرابط غير صالح أو الملف كبيراً جداً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return

    # إضافة الكتاب إلى قسم "غير مصنف"
    cat_id = ensure_uncategorized_category()
    success, author_id = db.add_author(author, cat_id)

    if not success:
        authors = db.get_authors_by_category(cat_id)
        author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)

    if author_id:
        db.add_book(title, author_id, file_id=file_id, added_by=ADMIN_ID)
        await query.edit_message_text(
            f"✅ *تم تنزيل الكتاب وإضافته بنجاح!*\n📖 {title}\n✍️ {author}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ فشل إضافة المؤلف.",
            reply_markup=admin_panel_keyboard()
        )


# المعالج الذي سنسجله في main.py مع أولوية عالية (group=1)
admin_download_handler = CallbackQueryHandler(
    admin_download_and_add_book,
    pattern="^add_search_result$"
  )
