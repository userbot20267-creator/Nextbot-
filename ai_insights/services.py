# ai_insights/services.py
import aiohttp
import database as db
from config import OPENROUTER_API_KEY

async def get_library_stats() -> dict:
    """جمع إحصائيات شاملة عن المكتبة لتحليلها"""
    stats = {
        "total_books": db.count_books(),
        "total_categories": len(db.get_all_categories()),
        "total_users": db.count_users(),
        "total_downloads": db.get_total_downloads(),
        "books_without_description": db.count_books_without_description(),
        "categories_stats": db.get_categories_stats(limit=5),
        "top_books": db.get_top_books(5),
        "recent_books": db.get_recent_books(5),
    }
    return stats

async def generate_insights(stats: dict) -> str:
    """إرسال الإحصائيات إلى OpenRouter (Gemini) لإنتاج تقرير تحليلي ذكي بالعربية"""
    if not OPENROUTER_API_KEY:
        return "⚠️ مفتاح OpenRouter غير موجود. لا يمكن توليد التحليل."

    # بناء نص الإحصائيات لتمريره للنموذج
    categories_text = "\n".join([f"- {c['name']}: {c['book_count']} كتب، {c['downloads']} تحميل" for c in stats['categories_stats']])
    top_books_text = "\n".join([f"{i+1}. {b['title']} ({b['downloads']} تحميل)" for i, b in enumerate(stats['top_books'])])
    recent_books_text = "\n".join([f"- {b['title']} ({b['category']})" for b in stats['recent_books']])

    prompt = f"""أنت مستشار متخصص في إدارة المكتبات الرقمية على تيليجرام. قم بتحليل البيانات التالية وقدم تقريراً احترافياً باللغة العربية يتضمن:
1. ملخص عام عن صحة المكتبة.
2. الأقسام الأقوى والأضعف مع توصيات لتحسينها.
3. تحليل لتفاعل المستخدمين (التحميلات).
4. اقتراحات ذكية (مثلاً: أقسام جديدة يمكن إضافتها، أو أنواع كتب ناقصة).
5. تقييم عام للمكتبة.

البيانات:
- إجمالي الكتب: {stats['total_books']}
- إجمالي الأقسام: {stats['total_categories']}
- إجمالي المستخدمين: {stats['total_users']}
- إجمالي التحميلات: {stats['total_downloads']}
- كتب بدون وصف: {stats['books_without_description']}

أكثر 5 أقسام نشاطاً (عدد الكتب والتحميلات):
{categories_text}

أكثر 5 كتب تحميلاً:
{top_books_text}

آخر 5 كتب مضافة:
{recent_books_text}

قدم التقرير بشكل منظم ومفيد لمالك المكتبة."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 1200
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return f"❌ فشل الاتصال بـ OpenRouter (كود: {resp.status})"
    except Exception as e:
        return f"❌ خطأ أثناء التحليل: {str(e)}"
