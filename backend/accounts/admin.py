from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import PasswordResetCode, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Inventory profile", {"fields": ("nickname",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Inventory profile", {"fields": ("email", "nickname")}),
    )
    list_display = ("username", "email", "nickname", "is_staff", "is_active")
    search_fields = ("username", "email", "nickname")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "attempts", "created_at")
    list_filter = ("used_at", "expires_at", "created_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("code_hash", "created_at")
