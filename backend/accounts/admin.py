from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


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
