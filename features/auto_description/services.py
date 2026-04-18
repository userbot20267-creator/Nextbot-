import aiohttp
from config import OPENROUTER_API_KEY

async def generate_book_description(title: str, author: str) -> str:
    if not OPENROUTER_API_KEY:
        return ""
    prompt = f"""اكتب وصفاً جذاباً وتسويقياً باللغة العربية لكتاب "{title}" للمؤلف {author}.
يجب أن يكون الوصف مشوقاً ويشجع على القراءة، حوالي 50-80 كلمة. اكتب الوصف فقط بدون أي مقدمات."""
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                return ""
    except Exception as e:
        print(f"خطأ في توليد الوصف: {e}")
        return ""
