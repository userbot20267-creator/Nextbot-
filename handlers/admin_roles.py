# handlers/admin_roles.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import database as db
from config import ADMIN_ID

# حالات المحادثة لإضافة مساعد
WAITING_ADMIN_ID, WAITING_PERMISSIONS = range(2)


# ---------- دوال التحقق من الصلاحية ----------
def is_owner(update: Update) -> bool:
    """التحقق من أن المستخدم هو المالك الأساسي"""
    return update.effective_user.id == ADMIN_ID


async def owner_only(update: Update) -> bool:
    """تزيين الدالة للتحقق من صلاحية المالك فقط"""
    if not is_owner(update):
        if update.callback_query:
            await update.callback_query.answer("⛔ هذه الصلاحية للمالك الأساسي فقط.", show_alert=True)
        else:
            await update.message.reply_text("⛔ هذه الصلاحية للمالك الأساسي فقط.")
        return False
    return True


# ---------- أمر /addadmin ----------
async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إضافة مساعد جديد"""
    if not await owner_only(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "🆔 *أرسل معرف المستخدم (ID) الذي تريد إضافته كمساعد:*\n\n"
        "يمكنك الحصول على المعرف من @userinfobot.\n"
        "أرسل /cancel للإلغاء.",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_ADMIN_ID


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال معرف المستخدم وعرض خيارات الصلاحيات"""
    try:
        user_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ معرف غير صحيح. أرسل رقماً صحيحاً.")
        return WAITING_ADMIN_ID

    if user_id == ADMIN_ID:
        await update.message.reply_text("❌ هذا هو المالك الأساسي بالفعل.")
        return ConversationHandler.END

    context.user_data["new_admin_id"] = user_id

    # عرض أزرار اختيار الصلاحيات
    keyboard = [
        [InlineKeyboardButton("📚 إدارة الكتب", callback_data="perm_books")],
        [InlineKeyboardButton("📁 إدارة الأقسام", callback_data="perm_categories")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="perm_users")],
        [InlineKeyboardButton("📣 إذاعة", callback_data="perm_broadcast")],
        [InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="perm_stats")],
        [InlineKeyboardButton("✅ تم الانتهاء", callback_data="perm_done")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="perm_cancel")],
    ]
    context.user_data["selected_perms"] = {
        "books": False, "categories": False, "users": False,
        "broadcast": False, "stats": True
    }

    await update.message.reply_text(
        "⚙️ *اختر الصلاحيات التي تريد منحها:*\n\n"
        "• الإحصائيات مفعلة افتراضياً.\n"
        "• اضغط على الصلاحية لتحديدها/إلغائها.\n"
        "• اضغط 'تم الانتهاء' عند الانتهاء.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_PERMISSIONS


async def toggle_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تبديل حالة الصلاحية المحددة"""
    query = update.callback_query
    await query.answer()

    perm_map = {
        "perm_books": "books",
        "perm_categories": "categories",
        "perm_users": "users",
        "perm_broadcast": "broadcast",
        "perm_stats": "stats"
    }
    perm_key = perm_map.get(query.data)
    if perm_key:
        perms = context.user_data.get("selected_perms", {})
        perms[perm_key] = not perms.get(perm_key, False)
        context.user_data["selected_perms"] = perms

        # تحديث النص
        status = "✅ مفعل" if perms[perm_key] else "❌ معطل"
        await query.answer(f"تم تغيير حالة الصلاحية: {status}")

        # إعادة عرض نفس القائمة
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if perms.get('books', False) else '❌'} إدارة الكتب",
                callback_data="perm_books"
            )],
            [InlineKeyboardButton(
                f"{'✅' if perms.get('categories', False) else '❌'} إدارة الأقسام",
                callback_data="perm_categories"
            )],
            [InlineKeyboardButton(
                f"{'✅' if perms.get('users', False) else '❌'} إدارة المستخدمين",
                callback_data="perm_users"
            )],
            [InlineKeyboardButton(
                f"{'✅' if perms.get('broadcast', False) else '❌'} إذاعة",
                callback_data="perm_broadcast"
            )],
            [InlineKeyboardButton(
                f"{'✅' if perms.get('stats', True) else '❌'} عرض الإحصائيات",
                callback_data="perm_stats"
            )],
            [InlineKeyboardButton("✅ تم الانتهاء", callback_data="perm_done")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="perm_cancel")],
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "perm_done":
        perms = context.user_data.get("selected_perms", {})
        user_id = context.user_data.get("new_admin_id")

        success = db.add_admin(
            user_id=user_id,
            added_by=ADMIN_ID,
            can_manage_books=perms.get("books", False),
            can_manage_categories=perms.get("categories", False),
            can_manage_users=perms.get("users", False),
            can_broadcast=perms.get("broadcast", False),
            can_view_stats=perms.get("stats", True)
        )

        if success:
            await query.edit_message_text(
                f"✅ *تم إضافة المساعد بنجاح!*\n\n🆔 `{user_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ فشل إضافة المساعد. حاول مرة أخرى.")
        return ConversationHandler.END
    elif query.data == "perm_cancel":
        await query.edit_message_text("❌ تم إلغاء العملية.")
        return ConversationHandler.END

    return WAITING_PERMISSIONS


async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء العملية"""
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END


# ---------- أمر /removeadmin ----------
async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف مساعد إداري"""
    if not await owner_only(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text("❌ استخدم: /removeadmin <معرف_المستخدم>")
        return

    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ معرف غير صحيح.")
        return

    if db.remove_admin(user_id):
        await update.message.reply_text(f"✅ تم حذف المساعد `{user_id}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ لم يتم العثور على هذا المساعد.")


# ---------- أمر /listadmins ----------
async def list_admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة المساعدين الإداريين"""
    if not await owner_only(update):
        return

    admins = db.get_all_admins()
    if not admins:
        await update.message.reply_text("📭 لا يوجد مساعدون إداريون حالياً.")
        return

    text = "👥 *قائمة المساعدين الإداريين:*\n\n"
    for user_id, added_by, added_at in admins:
        added_date = added_at.strftime("%Y-%m-%d") if added_at else "غير معروف"
        text += f"🆔 `{user_id}` - أضيف في {added_date}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ---------- تجميع الـ Handlers ----------
admin_roles_handlers = [
    CommandHandler("addadmin", add_admin_start),
    CommandHandler("removeadmin", remove_admin_cmd),
    CommandHandler("listadmins", list_admins_cmd),
]

admin_roles_conversation = ConversationHandler(
    entry_points=[CommandHandler("addadmin", add_admin_start)],
    states={
        WAITING_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id)],
        WAITING_PERMISSIONS: [CallbackQueryHandler(toggle_permission, pattern="^perm_")],
    },
    fallbacks=[CommandHandler("cancel", cancel_operation)],
      )
