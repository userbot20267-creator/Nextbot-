# models/schemas.py

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List
from datetime import datetime


# ========== نماذج المستخدم ==========
class UserSchema(BaseModel):
    """نموذج بيانات المستخدم"""
    user_id: int = Field(..., gt=0, description="معرف المستخدم في تليجرام")
    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    joined_at: Optional[datetime] = None
    is_banned: bool = False
    last_activity: Optional[datetime] = None

    @validator('user_id')
    def user_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('معرف المستخدم يجب أن يكون رقماً موجباً')
        return v

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": 123456789,
                "username": "john_doe",
                "first_name": "John",
                "last_name": "Doe",
                "is_banned": False
            }
        }


class UserStatsSchema(BaseModel):
    """نموذج إحصائيات المستخدمين"""
    total_users: int = 0
    active_today: int = 0
    banned_users: int = 0


# ========== نماذج الأقسام ==========
class CategorySchema(BaseModel):
    """نموذج بيانات القسم"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100, description="اسم القسم")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('اسم القسم لا يمكن أن يكون فارغاً')
        return v.strip()

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "روايات"
            }
        }


class CategoryStatsSchema(BaseModel):
    """نموذج إحصائيات الأقسام"""
    category_id: int
    name: str
    total_downloads: int


# ========== نماذج المؤلفين ==========
class AuthorSchema(BaseModel):
    """نموذج بيانات المؤلف"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200, description="اسم المؤلف")
    category_id: int = Field(..., gt=0, description="معرف القسم المرتبط")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('اسم المؤلف لا يمكن أن يكون فارغاً')
        return v.strip()

    @validator('category_id')
    def category_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('معرف القسم يجب أن يكون رقماً موجباً')
        return v

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 5,
                "name": "نجيب محفوظ",
                "category_id": 1
            }
        }


# ========== نماذج الكتب ==========
class BookSchema(BaseModel):
    """نموذج بيانات الكتاب"""
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=500, description="عنوان الكتاب")
    author_id: int = Field(..., gt=0, description="معرف المؤلف")
    file_id: Optional[str] = Field(None, description="معرف الملف في تليجرام")
    file_link: Optional[str] = Field(None, description="رابط خارجي للكتاب")
    added_by: Optional[int] = Field(None, description="معرف المستخدم الذي أضاف الكتاب")
    download_count: int = Field(0, ge=0, description="عدد مرات التحميل")
    created_at: Optional[datetime] = None

    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('عنوان الكتاب لا يمكن أن يكون فارغاً')
        return v.strip()

    @validator('author_id')
    def author_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('معرف المؤلف يجب أن يكون رقماً موجباً')
        return v

    @validator('file_link')
    def validate_file_link(cls, v):
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                raise ValueError('رابط الملف يجب أن يبدأ بـ http:// أو https://')
        return v

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "title": "الخيميائي",
                "author_id": 10,
                "file_link": "https://example.com/book.pdf",
                "download_count": 42
            }
        }


class BookStatsSchema(BaseModel):
    """نموذج إحصائيات الكتب الأكثر تحميلاً"""
    book_id: int
    title: str
    author_name: str
    download_count: int


class BookDetailSchema(BaseModel):
    """نموذج تفاصيل الكتاب مع المؤلف والقسم"""
    id: int
    title: str
    file_id: Optional[str]
    file_link: Optional[str]
    download_count: int
    author_name: str
    category_name: str


# ========== نماذج الإعدادات ==========
class SettingSchema(BaseModel):
    """نموذج بيانات الإعدادات"""
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)

    @validator('key')
    def key_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError('مفتاح الإعداد لا يمكن أن يكون فارغاً')
        return v.strip()

    @validator('value')
    def value_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('قيمة الإعداد لا يمكن أن تكون فارغة')
        return v.strip()

    class Config:
        orm_mode = True


class RequiredChannelSchema(BaseModel):
    """نموذج القناة الإجبارية"""
    channel: str = Field(..., min_length=1, description="معرف القناة (@username أو -100xxx)")

    @validator('channel')
    def validate_channel_format(cls, v):
        if not v.startswith(('@', '-100')):
            raise ValueError('معرف القناة يجب أن يبدأ بـ @ أو -100')
        return v


# ========== نماذج البحث ==========
class SearchQuerySchema(BaseModel):
    """نموذج استعلام البحث"""
    query: str = Field(..., min_length=1, max_length=200)

    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('نص البحث لا يمكن أن يكون فارغاً')
        return v.strip()


class ExternalBookResultSchema(BaseModel):
    """نموذج نتيجة البحث الخارجي"""
    title: str
    author: str
    link: str

    @validator('link')
    def link_must_be_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('الرابط يجب أن يكون صحيحاً')
        return v


class SearchResultsSchema(BaseModel):
    """نموذج نتائج البحث المجمعة"""
    local_results: List[BookDetailSchema] = []
    external_results: List[ExternalBookResultSchema] = []
    total_count: int = 0


# ========== نماذج الإذاعة ==========
class BroadcastMessageSchema(BaseModel):
    """نموذج رسالة الإذاعة"""
    text: str = Field(..., min_length=1, max_length=4096)
    parse_mode: Optional[str] = Field("HTML", regex="^(HTML|Markdown|MarkdownV2)$")

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('نص الرسالة لا يمكن أن يكون فارغاً')
        return v.strip()


class BroadcastResultSchema(BaseModel):
    """نموذج نتيجة الإذاعة"""
    success_count: int
    failed_count: int
    total_users: int


# ========== نماذج الحظر ==========
class BanUserSchema(BaseModel):
    """نموذج حظر مستخدم"""
    user_id: int = Field(..., gt=0)

    @validator('user_id')
    def user_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('معرف المستخدم يجب أن يكون رقماً موجباً')
        return v


# ========== نماذج التغذية الراجعة ==========
class FeedbackSchema(BaseModel):
    """نموذج رسالة المستخدم للإدارة"""
    user_id: int
    message: str = Field(..., min_length=1, max_length=2000)

    @validator('message')
    def message_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('الرسالة لا يمكن أن تكون فارغة')
        return v.strip()


# ========== نماذج الردود العامة ==========
class SuccessResponseSchema(BaseModel):
    """نموذج رد النجاح"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponseSchema(BaseModel):
    """نموذج رد الخطأ"""
    success: bool = False
    error: str
    details: Optional[str] = None
