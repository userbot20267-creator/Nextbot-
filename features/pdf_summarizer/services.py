# features/pdf_summarizer/services.py
import aiohttp
import tempfile
import os
from PyPDF2 import PdfReader
from config import OPENROUTER_API_KEY


async def extract_text_from_pdf(file_id: str, context) -> str:
    """
    تنزيل ملف PDF من تليجرام واستخراج النص من أول 15 صفحة.
    
    Args:
        file_id: معرف الملف في تليجرام
        context: context من python-telegram-bot
    
    Returns:
        النص المستخرج (حد أقصى 6000 حرف)
    """
    try:
        # تنزيل الملف من تليجرام
        file = await context.bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        # استخراج النص من PDF
        text = ""
        with open(tmp_path, "rb") as f:
            reader = PdfReader(f)
            pages = min(len(reader.pages), 15)  # أول 15 صفحة كحد أقصى
            for i in range(pages):
                try:
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    print(f"خطأ في استخراج الصفحة {i}: {e}")
                    continue

        # حذف الملف المؤقت
        os.unlink(tmp_path)

        # تنظيف النص وقصه إلى 6000 حرف (حد OpenRouter للسياق)
        text = text.strip().replace("\n\n\n", "\n").replace("  ", " ")
        return text[:6000]

    except Exception as e:
        print(f"خطأ في extract_text_from_pdf: {e}")
        return ""


async def summarize_pdf_content(text: str, title: str, author: str) -> str:
    """
    إرسال النص المستخرج إلى OpenRouter للحصول على ملخص باللغة العربية.
    
    Args:
        text: النص المستخرج من PDF
        title: عنوان الكتاب
        author: اسم المؤلف
    
    Returns:
        الملخص باللغة العربية
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ مفتاح OpenRouter غير مضبوط. لا يمكن التلخيص."

    if not text or len(text) < 100:
        return "⚠️ النص المستخرج قصير جداً أو فارغ. لا يمكن تلخيصه."

    prompt = f"""أنت مساعد ذكي لتلخيص الكتب.
لخص محتوى كتاب "{title}" للمؤلف {author} بناءً على النص المقتطف التالي.
اكتب ملخصاً شاملاً ومفيداً باللغة العربية في 150-300 كلمة، يركز على:
- الموضوع الرئيسي للكتاب
- الأفكار الأساسية
- الفئة المستهدفة

النص المقتطف:
{text}

الملخص:"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "choices" in data and data["choices"]:
                        return data["choices"][0]["message"]["content"].strip()
                return "❌ فشل الحصول على ملخص من OpenRouter."

    except aiohttp.ClientError as e:
        print(f"خطأ في الاتصال بـ OpenRouter: {e}")
        return "❌ خطأ في الاتصال بخدمة التلخيص."
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        return "❌ حدث خطأ غير متوقع أثناء التلخيص."
