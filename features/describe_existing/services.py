# features/describe_existing/services.py
import aiohttp
from config import OPENROUTER_API_KEY


async def generate_description(title: str, author: str) -> str:
    """
    توليد وصف جذاب باللغة العربية لكتاب باستخدام OpenRouter (Gemini).

    Args:
        title: عنوان الكتاب
        author: اسم المؤلف

    Returns:
        الوصف المقترح، أو رسالة خطأ مناسبة.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ مفتاح OpenRouter غير موجود. لا يمكن توليد الوصف."

    # تحضير النموذج والطلب
    prompt = f"""اكتب وصفاً جذاباً وتسويقياً باللغة العربية لكتاب "{title}" للمؤلف {author}.
يجب أن يكون الوصف مشوقاً ويشجع على القراءة، حوالي 50-80 كلمة. اكتب الوصف فقط بدون أي مقدمات أو تعليقات إضافية."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.0-flash-exp:free",  # نموذج مجاني وسريع
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,   # إبداع معقول
        "max_tokens": 300     # كافٍ لوصف 50-80 كلمة
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "choices" in data and data["choices"]:
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        return "❌ استجابة غير متوقعة من OpenRouter."
                elif resp.status == 401:
                    return "❌ مفتاح OpenRouter غير صالح."
                elif resp.status == 429:
                    return "❌ تم تجاوز الحد المسموح للطلبات. حاول لاحقاً."
                else:
                    return f"❌ فشل الاتصال بـ OpenRouter (كود: {resp.status})"

    except aiohttp.ClientError as e:
        return f"❌ خطأ في الاتصال بالإنترنت: {e}"
    except Exception as e:
        return f"❌ خطأ غير متوقع: {e}"
