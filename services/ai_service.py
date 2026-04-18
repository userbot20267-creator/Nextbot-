# services/ai_service.py
import aiohttp
import asyncio
import json
import re
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
        "model": "google/gemini-2.0-flash-exp:free",  # Free or preferred model
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


# ---------- دوال جديدة للبحث الذكي ----------
async def ai_search_book(query: str) -> dict | None:
    """استخدام OpenRouter لتحليل طلب المستخدم واستخراج عنوان الكتاب واسم المؤلف."""
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY غير موجود.")
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # تحسين الصيغة لإجبار النموذج على إخراج JSON فقط
    prompt = f"""استخرج عنوان الكتاب واسم المؤلف من النص التالي. أعد النتيجة بصيغة JSON صالحة فقط، بدون أي تعليقات إضافية.
مثال: {{"title": "الخيميائي", "author": "باولو كويلو"}}
النص: "{query}"
JSON:"""

    payload = {
        "model": "google/gemini-2.0-flash-exp:free",  # يمكن تغييره إلى "openai/gpt-3.5-turbo" إذا استمرت المشكلة
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 150
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    print(f"⚠️ OpenRouter API error: {resp.status}")
                    return None
                
                data = await resp.json()
                if "choices" not in data:
                    print("❌ الاستجابة لا تحتوي على 'choices'")
                    return None
                
                content = data["choices"][0]["message"]["content"].strip()
                print(f"🔍 استجابة النموذج: {content}")  # للتشخيص
                
                # محاولة استخراج JSON باستخدام تعبير منتظم
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group()
                else:
                    # إذا فشل، حاول إصلاح الأخطاء الشائعة (مثل علامات التنصيص)
                    content = content.replace("'", '"')
                
                result = json.loads(content)
                return {
                    "title": result.get("title", "غير معروف"),
                    "author": result.get("author", "غير معروف")
                }
    except json.JSONDecodeError as e:
        print(f"⚠️ فشل تحليل JSON: {e}\nالمحتوى: {content}")
        # محاولة أخيرة: استخراج يدوي إذا كان النص بسيطاً
        if "title" in content.lower() and "author" in content.lower():
            # محاولة بدائية لاستخراج القيم
            title_match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
            author_match = re.search(r'"author"\s*:\s*"([^"]*)"', content)
            if title_match and author_match:
                return {"title": title_match.group(1), "author": author_match.group(1)}
        return None
    except asyncio.TimeoutError:
        print("⚠️ مهلة OpenRouter للبحث الذكي")
        return None
    except Exception as e:
        print(f"❌ خطأ في ai_search_book: {e}")
        return None


async def find_book_download_url(title: str, author: str = "") -> str | None:
    """البحث عن رابط تحميل PDF للكتاب من OpenLibrary (يفضل Internet Archive)."""
    search_query = title
    if author and author != "غير معروف":
        search_query += f" {author}"
    
    url = "https://openlibrary.org/search.json"
    params = {
        "q": search_query,
        "limit": 5,
        "fields": "title,author_name,cover_edition_key,edition_key,ia"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                docs = data.get("docs", [])
                if not docs:
                    return None

                for doc in docs:
                    ia_id = doc.get("ia")
                    if ia_id:
                        return f"https://archive.org/download/{ia_id}/{ia_id}.pdf"
                    
                    edition_key = doc.get("cover_edition_key")
                    if not edition_key and doc.get("edition_key"):
                        edition_key = doc["edition_key"][0] if isinstance(doc["edition_key"], list) else doc["edition_key"]
                    
                    if edition_key:
                        return f"https://openlibrary.org/books/{edition_key}"
                
                return None
                
        except asyncio.TimeoutError:
            print(f"⚠️ مهلة البحث في OpenLibrary للعنوان: {title}")
            return None
        except Exception as e:
            print(f"❌ خطأ في find_book_download_url: {e}")
            return None
