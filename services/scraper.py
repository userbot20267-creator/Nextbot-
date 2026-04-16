# services/scraper.py

import aiohttp
import asyncio
import os
from typing import List, Tuple, Optional, Dict, Any

# مفتاح Google Books API (اختياري، يمكن تركه فارغاً)
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", None)

# ---------- البحث في Open Library ----------
async def search_open_library(query: str, limit: int = 5) -> List[Tuple[str, str, str]]:
    """
    البحث في Open Library API عن الكتب.
    
    Args:
        query: نص البحث (عنوان أو مؤلف)
        limit: عدد النتائج المطلوبة
    
    Returns:
        قائمة تحتوي على (العنوان, المؤلف, الرابط)
    """
    url = "https://openlibrary.org/search.json"
    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,cover_edition_key,edition_key,first_publish_year"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                results = []
                
                for doc in data.get("docs", []):
                    title = doc.get("title", "غير معروف")
                    
                    # استخراج اسم المؤلف
                    author = "غير معروف"
                    if doc.get("author_name"):
                        author = doc["author_name"][0]
                    
                    # إنشاء رابط للكتاب
                    link = f"https://openlibrary.org/search?q={query.replace(' ', '+')}"
                    if "cover_edition_key" in doc:
                        link = f"https://openlibrary.org/books/{doc['cover_edition_key']}"
                    elif "edition_key" in doc and doc["edition_key"]:
                        link = f"https://openlibrary.org/books/{doc['edition_key'][0]}"
                    
                    results.append((title, author, link))
                
                return results[:limit]
                
        except asyncio.TimeoutError:
            print(f"⚠️ مهلة البحث في Open Library انتهت للاستعلام: {query}")
            return []
        except aiohttp.ClientError as e:
            print(f"❌ خطأ في الاتصال بـ Open Library: {e}")
            return []
        except Exception as e:
            print(f"❌ خطأ غير متوقع في Open Library: {e}")
            return []


# ---------- البحث في Google Books ----------
async def search_google_books(query: str, limit: int = 5) -> List[Tuple[str, str, str]]:
    """
    البحث في Google Books API عن الكتب.
    
    Args:
        query: نص البحث
        limit: عدد النتائج
    
    Returns:
        قائمة تحتوي على (العنوان, المؤلف, الرابط)
    """
    if not GOOGLE_BOOKS_API_KEY:
        return []
    
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "key": GOOGLE_BOOKS_API_KEY,
        "maxResults": limit,
        "langRestrict": "ar,en",  # العربية والإنجليزية
        "printType": "books"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                results = []
                
                for item in data.get("items", []):
                    info = item.get("volumeInfo", {})
                    title = info.get("title", "غير معروف")
                    
                    authors = info.get("authors", ["غير معروف"])
                    author = authors[0] if authors else "غير معروف"
                    
                    link = info.get("infoLink") or info.get("canonicalVolumeLink") or ""
                    if not link and "id" in item:
                        link = f"https://books.google.com/books?id={item['id']}"
                    
                    if link:
                        results.append((title, author, link))
                
                return results[:limit]
                
        except asyncio.TimeoutError:
            print(f"⚠️ مهلة البحث في Google Books انتهت للاستعلام: {query}")
            return []
        except aiohttp.ClientError as e:
            print(f"❌ خطأ في الاتصال بـ Google Books: {e}")
            return []
        except Exception as e:
            print(f"❌ خطأ غير متوقع في Google Books: {e}")
            return []


# ---------- البحث الخارجي المجمع ----------
async def search_external_books(query: str, limit: int = 10) -> List[Tuple[str, str, str]]:
    """
    البحث في جميع المصادر الخارجية بشكل متوازٍ.
    
    Args:
        query: نص البحث
        limit: الحد الأقصى لعدد النتائج المجمعة
    
    Returns:
        قائمة منسقة من النتائج (عنوان, مؤلف, رابط)
    """
    # تشغيل المهمتين بالتوازي
    open_lib_task = search_open_library(query, limit=5)
    google_task = search_google_books(query, limit=5)
    
    open_results, google_results = await asyncio.gather(
        open_lib_task, 
        google_task,
        return_exceptions=True
    )
    
    # معالجة الأخطاء المحتملة
    if isinstance(open_results, Exception):
        print(f"خطأ في Open Library: {open_results}")
        open_results = []
    if isinstance(google_results, Exception):
        print(f"خطأ في Google Books: {google_results}")
        google_results = []
    
    # دمج النتائج مع إزالة التكرار (عبر مقارنة بسيطة للعناوين)
    combined = []
    seen_titles = set()
    
    for title, author, link in open_results + google_results:
        normalized_title = title.lower().strip()
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            combined.append((title, author, link))
    
    return combined[:limit]


# ---------- جلب تفاصيل كتاب من Open Library ----------
async def fetch_book_details_open_library(book_id: str) -> Optional[Dict[str, Any]]:
    """
    جلب تفاصيل كتاب معين من Open Library عبر معرف العمل (work id).
    
    Args:
        book_id: معرف العمل في Open Library (مثل OL12345W)
    
    Returns:
        قاموس يحتوي على تفاصيل الكتاب أو None
    """
    url = f"https://openlibrary.org/works/{book_id}.json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"خطأ في جلب تفاصيل الكتاب من Open Library: {e}")
            return None


# ---------- جلب تفاصيل كتاب من Google Books ----------
async def fetch_book_details_google(book_id: str) -> Optional[Dict[str, Any]]:
    """
    جلب تفاصيل كتاب معين من Google Books عبر معرف المجلد.
    
    Args:
        book_id: معرف المجلد في Google Books
    
    Returns:
        قاموس يحتوي على تفاصيل الكتاب أو None
    """
    if not GOOGLE_BOOKS_API_KEY:
        return None
    
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
    params = {"key": GOOGLE_BOOKS_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"خطأ في جلب تفاصيل الكتاب من Google Books: {e}")
            return None


# ---------- دالة موحدة لجلب التفاصيل (تكتشف المصدر تلقائياً) ----------
async def fetch_book_details(book_id: str, source: str = "auto") -> Optional[Dict[str, Any]]:
    """
    جلب تفاصيل كتاب من المصدر المناسب.
    
    Args:
        book_id: معرف الكتاب
        source: "openlibrary", "google", أو "auto" للاكتشاف التلقائي
    
    Returns:
        قاموس يحتوي على تفاصيل الكتاب
    """
    if source == "auto":
        # اكتشاف المصدر من صيغة المعرف
        if book_id.startswith("OL") and book_id.endswith("W"):
            source = "openlibrary"
        elif len(book_id) == 12 and book_id.isalnum():
            source = "google"
        else:
            return None
    
    if source == "openlibrary":
        return await fetch_book_details_open_library(book_id)
    elif source == "google":
        return await fetch_book_details_google(book_id)
    else:
        return None


# ---------- البحث عن غلاف الكتاب ----------
async def get_book_cover_url(title: str, author: str = "") -> Optional[str]:
    """
    محاولة الحصول على رابط غلاف كتاب باستخدام Open Library Covers API.
    
    Args:
        title: عنوان الكتاب
        author: اسم المؤلف (اختياري)
    
    Returns:
        رابط صورة الغلاف أو None
    """
    # البحث عن ISBN أو معرف الغلاف
    query = f"{title} {author}".strip()
    url = "https://openlibrary.org/search.json"
    params = {"q": query, "limit": 1, "fields": "cover_i,isbn"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                docs = data.get("docs", [])
                if docs and "cover_i" in docs[0]:
                    cover_id = docs[0]["cover_i"]
                    return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                elif docs and "isbn" in docs[0]:
                    isbn = docs[0]["isbn"][0]
                    return f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
        except Exception:
            pass
    return None
# ---------- تحميل ملف من رابط ----------
import aiohttp
import aiofiles
import os
import tempfile

async def download_file_from_url(url: str) -> str | None:
    """
    تحميل ملف من رابط وحفظه مؤقتاً، ثم رفعه إلى تليجرام وإرجاع file_id.
    إذا فشل التحميل أو كان الرابط ليس ملفاً مباشراً، ترجع None.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return None
                
                # قراءة المحتوى
                content = await resp.read()
                
                # التحقق من الحجم (حد تليجرام 50 ميجا)
                if len(content) > 50 * 1024 * 1024:
                    return None
                
                # حفظ مؤقت
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                return tmp_path
    except Exception as e:
        print(f"خطأ في تحميل الملف: {e}")
        return None
