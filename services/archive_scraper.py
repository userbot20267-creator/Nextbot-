# services/archive_scraper.py

import aiohttp
from typing import List, Tuple, Optional


async def search_internet_archive(query: str, limit: int = 5) -> List[Tuple[str, str, str, str]]:
    """
    البحث في Internet Archive عن الكتب المجانية.
    
    Args:
        query: نص البحث (عنوان أو مؤلف)
        limit: عدد النتائج المطلوبة
    
    Returns:
        قائمة تحتوي على (العنوان, المؤلف, رابط التحميل, رابط الغلاف)
        رابط الغلاف قد يكون None إذا لم يتوفر
    """
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"(title:({query}) OR creator:({query})) AND mediatype:texts",
        "fl[]": ["identifier", "title", "creator", "year", "downloads"],
        "sort[]": "downloads desc",
        "rows": limit,
        "output": "json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                docs = data.get("response", {}).get("docs", [])
                
                results = []
                for doc in docs:
                    identifier = doc.get("identifier")
                    if not identifier:
                        continue
                    
                    title = doc.get("title", "غير معروف")
                    creator = doc.get("creator", ["غير معروف"])[0] if doc.get("creator") else "غير معروف"
                    
                    # روابط التحميل المباشر (PDF غالباً)
                    download_url = f"https://archive.org/download/{identifier}/{identifier}.pdf"
                    
                    # رابط صورة الغلاف
                    cover_url = f"https://archive.org/services/img/{identifier}"
                    
                    results.append((title, creator, download_url, cover_url))
                
                return results[:limit]
                
        except aiohttp.ClientError as e:
            print(f"❌ خطأ في الاتصال بـ Internet Archive: {e}")
            return []
        except Exception as e:
            print(f"❌ خطأ غير متوقع في Internet Archive: {e}")
            return []


async def get_book_cover_from_archive(identifier: str) -> Optional[str]:
    """
    جلب رابط صورة غلاف كتاب من Internet Archive.
    
    Args:
        identifier: معرف الكتاب في archive.org
    
    Returns:
        رابط صورة الغلاف أو None
    """
    return f"https://archive.org/services/img/{identifier}"


async def get_direct_download_url(identifier: str, file_format: str = "pdf") -> Optional[str]:
    """
    الحصول على رابط تحميل مباشر لكتاب من Internet Archive.
    
    Args:
        identifier: معرف الكتاب
        file_format: صيغة الملف (pdf, epub, txt)
    
    Returns:
        رابط التحميل المباشر
    """
    formats = ["pdf", "epub", "txt", "djvu"]
    if file_format not in formats:
        file_format = "pdf"
    
    return f"https://archive.org/download/{identifier}/{identifier}.{file_format}"
