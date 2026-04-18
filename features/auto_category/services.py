import aiohttp
from config import OPENROUTER_API_KEY

async def suggest_category(title: str, author: str, existing_categories: list) -> str | None:
    if not OPENROUTER_API_KEY or not existing_categories:
        return None
    cats = ", ".join([name for _, name in existing_categories])
    prompt = f"""لدينا الأقسام التالية في مكتبة: {cats}.
أي قسم هو الأنسب لكتاب "{title}" للمؤلف {author}؟
أجب باسم القسم فقط (مطابق تماماً للقائمة). إذا لم تجد مناسباً، أجب "غير مصنف"."""
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 50
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                return None
    except Exception as e:
        print(f"خطأ في اقتراح القسم: {e}")
        return None
