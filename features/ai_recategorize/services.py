# features/ai_recategorize/services.py
import aiohttp
import asyncio
import database as db
from config import OPENROUTER_API_KEY


async def suggest_category(title: str, author: str, categories: list) -> str | None:
    """استخدام OpenRouter لاقتراح القسم الأنسب لكتاب معين"""
    if not OPENROUTER_API_KEY:
        return None

    cats = ", ".join([name for _, name in categories])
    prompt = f"""الأقسام المتاحة في المكتبة: {cats}.
اختر القسم الأنسب لكتاب "{title}" للمؤلف {author}.
أجب باسم القسم فقط (مطابق تماماً للقائمة). إذا لم تجد مناسباً، أجب "غير مصنف"."""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"خطأ في اقتراح القسم: {e}")
    return None


async def recategorize_books() -> tuple[int, int]:
    """إعادة تصنيف جميع الكتب في 'غير مصنف' وإرجاع (نجاح, فشل)"""
    categories = db.get_all_categories()
    if not categories:
        return 0, 0

    uncategorized_books = db.get_books_in_category("غير مصنف")
    if not uncategorized_books:
        return 0, 0

    success = 0
    failed = 0

    for book in uncategorized_books:
        book_id = book['id']
        title = book['title']
        author = book['author']

        suggestion = await suggest_category(title, author, categories)
        if suggestion:
            # البحث عن معرف القسم المطابق
            target_cat_id = None
            for cat_id, cat_name in categories:
                if cat_name == suggestion:
                    target_cat_id = cat_id
                    break

            if target_cat_id:
                # نقل الكتاب إلى القسم الجديد
                try:
                    db.move_book_to_category(book_id, target_cat_id)
                    success += 1
                except Exception as e:
                    print(f"فشل نقل الكتاب {book_id}: {e}")
                    failed += 1
            else:
                failed += 1
        else:
            failed += 1

        # تأخير بسيط لتجنب تجاوز حد OpenRouter
        await asyncio.sleep(0.5)

    return success, failed
