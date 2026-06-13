from django.contrib import admin

from .models import FloorPlan, Home


@admin.register(Home)
class HomeAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(FloorPlan)
class FloorPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "home", "width", "height", "unit", "created_at")
    list_filter = ("unit", "created_at", "updated_at")
    search_fields = ("name", "home__name", "home__owner__email")
