# services/auto_fetcher.py

import asyncio
from telegram import Bot
from services.scraper import search_external_books_enhanced, download_file_from_url
from services.auto_publisher import publish_book_to_channel
import database as db
from config import ADMIN_ID
import os


async def fetch_and_add_books(bot: Bot, keywords: list = None, limit_per_keyword: int = 3):
    """
    البحث عن كتب جديدة بناءً على كلمات مفتاحية وإضافتها تلقائياً.
    """
    if keywords is None:
        keywords = ["programming", "python", "history", "science", "novel"]

    total_added = 0

    for keyword in keywords:
        results = await search_external_books_enhanced(keyword, limit=limit_per_keyword)
        for title, author, link, cover_url in results:
            # التحقق من عدم وجود الكتاب مسبقاً (بسيط)
            existing = db.search_books(title)
            if existing:
                continue

            # تحميل الملف
            tmp_path = await download_file_from_url(link)
            file_id = None
            if tmp_path:
                try:
                    with open(tmp_path, 'rb') as f:
                        msg = await bot.send_document(chat_id=ADMIN_ID, document=f)
                        file_id = msg.document.file_id
                    os.unlink(tmp_path)
                except:
                    pass

            cat_id = ensure_uncategorized_category()
            success, author_id = db.add_author(author, cat_id)
            if not success:
                authors = db.get_authors_by_category(cat_id)
                author_id = next((a[0] for a in authors if a[1].lower() == author.lower()), None)

            if author_id:
                db.add_book(title, author_id, file_id=file_id, file_link=link, added_by=ADMIN_ID)
                # نشر في القناة
                await publish_book_to_channel(bot, title, author, file_id, link, cover_url)
                total_added += 1
                await asyncio.sleep(1)  # تجنب حدود المعدل

    return total_added


def ensure_uncategorized_category():
    # نفس الدالة الموجودة سابقاً
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


async def daily_auto_fetch(context):
    """المهمة اليومية للجلب التلقائي"""
    if not db.is_auto_fetch_enabled():
        return
    bot = context.bot
    added = await fetch_and_add_books(bot)
    if added > 0:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ *تم جلب {added} كتاباً جديداً تلقائياً.*",
            parse_mode="Markdown"
              )
