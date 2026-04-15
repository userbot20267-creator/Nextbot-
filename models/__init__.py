# models/__init__.py

from .schemas import (
    # نماذج المستخدم
    UserSchema,
    UserStatsSchema,
    
    # نماذج الأقسام
    CategorySchema,
    CategoryStatsSchema,
    
    # نماذج المؤلفين
    AuthorSchema,
    
    # نماذج الكتب
    BookSchema,
    BookStatsSchema,
    BookDetailSchema,
    
    # نماذج الإعدادات
    SettingSchema,
    RequiredChannelSchema,
    
    # نماذج البحث
    SearchQuerySchema,
    ExternalBookResultSchema,
    SearchResultsSchema,
    
    # نماذج الإذاعة
    BroadcastMessageSchema,
    BroadcastResultSchema,
    
    # نماذج الحظر
    BanUserSchema,
    
    # نماذج التغذية الراجعة
    FeedbackSchema,
    
    # نماذج الردود
    SuccessResponseSchema,
    ErrorResponseSchema,
)

__all__ = [
    "UserSchema",
    "UserStatsSchema",
    "CategorySchema",
    "CategoryStatsSchema",
    "AuthorSchema",
    "BookSchema",
    "BookStatsSchema",
    "BookDetailSchema",
    "SettingSchema",
    "RequiredChannelSchema",
    "SearchQuerySchema",
    "ExternalBookResultSchema",
    "SearchResultsSchema",
    "BroadcastMessageSchema",
    "BroadcastResultSchema",
    "BanUserSchema",
    "FeedbackSchema",
    "SuccessResponseSchema",
    "ErrorResponseSchema",
]
