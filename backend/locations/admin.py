from django.contrib import admin

from .models import LocationNode


@admin.register(LocationNode)
class LocationNodeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "node_type",
        "code",
        "full_code",
        "home",
        "floor_plan",
        "parent",
        "level",
        "sort_order",
    )
    list_filter = ("node_type", "home", "floor_plan", "level")
    search_fields = ("name", "code", "full_code", "path", "home__name")
    readonly_fields = ("full_code", "path", "level", "created_at", "updated_at")
    ordering = ("home", "floor_plan", "path", "sort_order")
