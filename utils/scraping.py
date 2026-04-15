# utils/scraping.py

import aiohttp
import asyncio
from typing import List, Tuple, Optional

# يمكنك الحصول على مفتاح Google Books مجاناً من Google Cloud Console
GOOGLE_BOOKS_API_KEY = None  # ضع المفتاح هنا أو استخدم متغير بيئي

async def search_open_library(query: str) -> List[Tuple[str, str, str]]:
    """
    البحث في Open Library API.
    ترجع قائمة بالنتائج: (عنوان, مؤلف, رابط الكتاب)
    """
    url = "https://openlibrary.org/search.json"
    params = {"q": query, "limit": 5}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for doc in data.get("docs", []):
                    title = doc.get("title", "غير معروف")
                    author = doc.get("author_name", ["غير معروف"])[0] if doc.get("author_name") else "غير معروف"
                    # إنشاء رابط للكتاب
                    if "cover_edition_key" in doc:
                        link = f"https://openlibrary.org/books/{doc['cover_edition_key']}"
                    elif "edition_key" in doc and doc["edition_key"]:
                        link = f"https://openlibrary.org/books/{doc['edition_key'][0]}"
                    else:
                        link = f"https://openlibrary.org/search?q={query.replace(' ', '+')}"
                    results.append((title, author, link))
                return results
        except Exception as e:
            print(f"خطأ في البحث في Open Library: {e}")
            return []

async def search_google_books(query: str) -> List[Tuple[str, str, str]]:
    """
    البحث في Google Books API (يتطلب مفتاح API).
    ترجع قائمة: (عنوان, مؤلف, رابط)
    """
    if not GOOGLE_BOOKS_API_KEY:
        return []  # تجاهل إذا لم يوجد مفتاح
    
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "key": GOOGLE_BOOKS_API_KEY, "maxResults": 5}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for item in data.get("items", []):
                    info = item.get("volumeInfo", {})
                    title = info.get("title", "غير معروف")
                    authors = info.get("authors", ["غير معروف"])
                    author = authors[0] if authors else "غير معروف"
                    link = info.get("infoLink", info.get("canonicalVolumeLink", ""))
                    if link:
                        results.append((title, author, link))
                return results
        except Exception as e:
            print(f"خطأ في البحث في Google Books: {e}")
            return []

async def search_external_books(query: str) -> List[Tuple[str, str, str]]:
    """
    يجمع نتائج البحث من عدة مصادر.
    يمكنك تعديل الأولويات حسب الحاجة.
    """
    # تشغيل المهمتين بالتوازي
    open_lib_task = search_open_library(query)
    google_task = search_google_books(query)
    
    open_results, google_results = await asyncio.gather(open_lib_task, google_task)
    
    # دمج النتائج (مع إزالة التكرار البسيط عن طريق العنوان)
    combined = open_results + google_results
    unique = []
    seen_titles = set()
    for title, author, link in combined:
        if title.lower() not in seen_titles:
            seen_titles.add(title.lower())
            unique.append((title, author, link))
    return unique[:10]  # إرجاع أول 10 نتائج

async def fetch_book_details(book_id: str, source: str = "openlibrary") -> Optional[dict]:
    """
    جلب تفاصيل إضافية لكتاب معين (غير مستخدم حالياً، للتوسع مستقبلاً).
    """
    if source == "openlibrary":
        url = f"https://openlibrary.org/works/{book_id}.json"
    else:
        return None
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            return None
