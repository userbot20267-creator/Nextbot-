# features/deep_link/services.py
from config import BOT_USERNAME


def generate_book_deep_link(book_id: int) -> str:
    """
    توليد رابط عميق لكتاب معين.
    مثال: https://t.me/YourBot?start=book_123
    """
    if not BOT_USERNAME:
        return ""
    return f"https://t.me/{BOT_USERNAME}?start=book_{book_id}"


def extract_book_id_from_start(args: list) -> int | None:
    """
    استخراج معرف الكتاب من وسائط أمر /start.
    يتوقع وجود وسيط مثل 'book_123'.
    """
    if not args:
        return None
    for arg in args:
        if arg.startswith("book_"):
            try:
                return int(arg[5:])
            except ValueError:
                return None
    return None
