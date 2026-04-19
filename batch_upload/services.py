# batch_upload/services.py
import database as db
from config import ADMIN_ID

async def process_batch_files(files_data: list, category_id: int, author_id: int) -> tuple:
    """معالجة دفعية للملفات: حفظها في قاعدة البيانات"""
    success = 0
    failed = 0
    
    for file_info in files_data:
        file_id = file_info["file_id"]
        title = file_info["file_name"].rsplit(".", 1)[0][:100]  # حد أقصى للعنوان
        
        try:
            db.add_book(title, author_id, file_id=file_id, added_by=ADMIN_ID)
            success += 1
        except Exception as e:
            print(f"فشل إضافة {title}: {e}")
            failed += 1
    
    return success, failed
