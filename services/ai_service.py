import aiohttp
from config import OPENROUTER_API_KEY

async def summarize_book_text(book_title, book_description=""):
    """Summarizes a book using OpenRouter API."""
    if not OPENROUTER_API_KEY:
        return "⚠️ عذراً، ميزة التلخيص غير مفعلة حالياً (OPENROUTER_API_KEY غير موجود)."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"قم بكتابة ملخص شامل وشيق لكتاب بعنوان '{book_title}' {f'ووصفه هو: {book_description}' if book_description else ''}. اجعل الملخص باللغة العربية، يركز على النقاط الرئيسية والدروس المستفادة، ولا يتجاوز 250 كلمة."
    
    payload = {
        "model": "google/gemini-2.0-flash-exp:free", # Free or preferred model
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                else:
                    return f"❌ حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي (كود: {response.status})."
    except Exception as e:
        return f"❌ خطأ غير متوقع: {str(e)}"
