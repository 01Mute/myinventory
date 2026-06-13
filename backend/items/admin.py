from django.contrib import admin

from .models import Category, Item, ItemLocationHistory, ItemTag, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "updated_at")
    search_fields = ("name", "owner__username", "owner__email")
    list_filter = ("created_at",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username", "owner__email")
    list_filter = ("created_at",)


class ItemTagInline(admin.TabularInline):
    model = ItemTag
    extra = 0
    autocomplete_fields = ("tag",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "category",
        "current_location_node",
        "quantity",
        "status",
        "last_checked_at",
    )
    list_filter = ("status", "category", "created_at", "updated_at")
    search_fields = (
        "name",
        "description",
        "owner__username",
        "owner__email",
        "current_location_node__full_code",
        "current_location_node__path",
        "tags__name",
    )
    autocomplete_fields = ("category", "current_location_node")
    inlines = (ItemTagInline,)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ItemLocationHistory)
class ItemLocationHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "from_location_node",
        "to_location_node",
        "moved_at",
        "created_by",
    )
    list_filter = ("moved_at", "created_at")
    search_fields = (
        "item__name",
        "from_location_node__full_code",
        "to_location_node__full_code",
        "memo",
    )
    autocomplete_fields = ("item", "from_location_node", "to_location_node", "created_by")
    readonly_fields = ("created_at",)
