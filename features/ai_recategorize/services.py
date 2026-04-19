# features/ai_recategorize/services.py
import aiohttp
import asyncio
import database as db
from config import OPENROUTER_API_KEY


async def suggest_category(title: str, author: str, categories: list) -> str | None:
    """
    استخدام OpenRouter (Gemini) لاقتراح القسم الأنسب لكتاب معين.

    Args:
        title: عنوان الكتاب
        author: اسم المؤلف
        categories: قائمة الأقسام المتاحة على شكل [(id, name), ...]

    Returns:
        اسم القسم المقترح (مطابق للقائمة) أو None إذا فشل الاقتراح.
    """
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY غير موجود.")
        return None

    # بناء قائمة بأسماء الأقسام فقط
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
                    if "choices" in data and data["choices"]:
                        return data["choices"][0]["message"]["content"].strip()
    except asyncio.TimeoutError:
        print(f"⚠️ مهلة OpenRouter للكتاب: {title}")
    except Exception as e:
        print(f"❌ خطأ في اقتراح القسم للكتاب {title}: {e}")

    return None


async def recategorize_books() -> tuple[int, int]:
    """
    إعادة تصنيف جميع الكتب الموجودة في قسم 'غير مصنف' باستخدام الذكاء الاصطناعي.
    لكل كتاب، يتم اقتراح قسم ونقله إليه.

    Returns:
        (عدد الكتب التي تم نقلها بنجاح, عدد الكتب التي فشل نقلها)
    """
    # 1. الحصول على جميع الأقسام
    categories = db.get_all_categories()
    if not categories:
        print("❌ لا توجد أقسام في المكتبة.")
        return 0, 0

    # 2. الحصول على الكتب في قسم 'غير مصنف'
    uncategorized_books = db.get_books_in_category("غير مصنف")
    if not uncategorized_books:
        print("ℹ️ لا توجد كتب في قسم 'غير مصنف'.")
        return 0, 0

    success = 0
    failed = 0

    for book in uncategorized_books:
        book_id = book['id']
        title = book['title']
        author = book['author']

        # 3. اقتراح قسم للكتاب
        suggestion = await suggest_category(title, author, categories)

        if suggestion:
            # البحث عن معرف القسم المطابق للاسم المقترح
            target_cat_id = None
            for cat_id, cat_name in categories:
                if cat_name == suggestion:
                    target_cat_id = cat_id
                    break

            if target_cat_id:
                try:
                    # 4. نقل الكتاب إلى القسم الجديد
                    # (تأكد من وجود دالة move_book_to_category في database.py)
                    db.move_book_to_category(book_id, target_cat_id)
                    success += 1
                    print(f"✅ تم نقل '{title}' إلى '{suggestion}'")
                except Exception as e:
                    print(f"❌ فشل نقل الكتاب {book_id} ('{title}'): {e}")
                    failed += 1
            else:
                print(f"⚠️ القسم المقترح '{suggestion}' غير موجود في القائمة.")
                failed += 1
        else:
            print(f"⚠️ فشل اقتراح قسم للكتاب '{title}'")
            failed += 1

        # تأخير بسيط لتجنب تجاوز حد معدل الطلبات لـ OpenRouter (خاصة للنماذج المجانية)
        await asyncio.sleep(0.5)

    return success, failed
