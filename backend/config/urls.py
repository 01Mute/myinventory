from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)
from homes.views import FloorPlanViewSet, HomeViewSet
from items.views import CategoryViewSet, ItemViewSet, TagViewSet
from locations.views import LocationNodeByFloorPlanView, LocationNodeViewSet


router = DefaultRouter()
router.register("homes", HomeViewSet, basename="home")
router.register("floor-plans", FloorPlanViewSet, basename="floor-plan")
router.register("location-nodes", LocationNodeViewSet, basename="location-node")
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")
router.register("items", ItemViewSet, basename="item")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "api/auth/password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "api/auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path(
        "api/floor-plans/<int:floor_plan_id>/location-nodes/",
        LocationNodeByFloorPlanView.as_view(),
        name="floor-plan-location-nodes",
    ),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
