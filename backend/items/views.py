import csv
import os
from pathlib import Path

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import response, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser

from locations.models import LocationNode
from .models import Category, Item, ItemLocationHistory, Tag
from .serializers import (
    CategorySerializer,
    ItemLocationHistorySerializer,
    ItemSerializer,
    MoveItemSerializer,
    TagSerializer,
)


def as_bool(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


def previous_location_id(location):
    return location.id if location else None


ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_PHOTO_BYTES = int(os.getenv("MAX_PHOTO_BYTES", str(10 * 1024 * 1024)))


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user).order_by("name", "id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(owner=self.request.user).order_by("name", "id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer

    # Query-parameter filters describe a collection, not a single row. Applying
    # them in get_queryset() also narrowed the detail routes, so a request like
    # GET /api/items/5/?q=zzz answered 404.
    filtered_actions = ("list", "export_csv", "touch_searched")

    def base_queryset(self):
        return (
            Item.objects.filter(owner=self.request.user)
            .select_related("category", "current_location_node")
            .prefetch_related("tags")
            .order_by("name", "id")
        )

    def get_queryset(self):
        qs = self.base_queryset()
        if self.action in self.filtered_actions:
            qs = self.apply_filters(qs)
        return qs

    def perform_update(self, serializer):
        previous_location = serializer.instance.current_location_node
        item = serializer.save()
        if previous_location_id(previous_location) != previous_location_id(item.current_location_node):
            ItemLocationHistory.objects.create(
                item=item,
                from_location_node=previous_location,
                to_location_node=item.current_location_node,
                memo="",
                moved_at=timezone.now(),
                created_by=self.request.user,
            )

    def apply_filters(self, qs):
        params = self.request.query_params
        q = params.get("q")
        category = params.get("category")
        tag = params.get("tag")
        location_code = params.get("location_code")
        location_node_id = params.get("location_node_id")
        status_value = params.get("status")

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(tags__name__icontains=q)
                | Q(current_location_node__full_code__icontains=q)
                | Q(current_location_node__path__icontains=q)
            ).distinct()

        if category:
            if category.isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(category__name__icontains=category)

        if tag:
            if tag.isdigit():
                qs = qs.filter(tags__id=int(tag))
            else:
                qs = qs.filter(tags__name__icontains=tag)

        if location_code:
            qs = qs.filter(current_location_node__full_code__icontains=location_code)

        if location_node_id:
            node = LocationNode.objects.filter(
                id=location_node_id,
                home__owner=self.request.user,
            ).first()
            if not node:
                return qs.none()
            if as_bool(params.get("include_children")):
                qs = qs.filter(current_location_node_id__in=node.get_descendant_ids())
            else:
                qs = qs.filter(current_location_node=node)

        if status_value:
            qs = qs.filter(status=status_value)

        return qs.distinct()

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        csv_response = HttpResponse(content_type="text/csv; charset=utf-8")
        csv_response["Content-Disposition"] = 'attachment; filename="items.csv"'
        csv_response.write("\ufeff")

        writer = csv.writer(csv_response)
        writer.writerow(
            [
                "물건",
                "위치코드",
                "위치",
                "카테고리",
                "수량",
                "태그",
                "구매일자",
                "마지막검색일자",
                "상태",
                "설명",
            ],
        )
        for item in qs:
            writer.writerow(
                [
                    item.name,
                    item.current_location_node.full_code if item.current_location_node else "",
                    item.current_location_node.path if item.current_location_node else "",
                    item.category.name if item.category else "",
                    item.quantity,
                    " ".join(f"#{tag.name}" for tag in item.tags.all()),
                    item.purchase_date.isoformat() if item.purchase_date else "",
                    item.last_checked_at.isoformat() if item.last_checked_at else "",
                    item.status,
                    item.description,
                ],
            )

        return csv_response

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def photo(self, request, pk=None):
        item = self.get_object()
        uploaded = request.FILES.get("photo")
        if not uploaded:
            return response.Response(
                {"photo": "사진 파일을 선택하세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Path(uploaded.name).suffix.lower() not in ALLOWED_PHOTO_EXTENSIONS:
            return response.Response(
                {"photo": "JPG, PNG, GIF, WEBP 사진 파일만 업로드할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if uploaded.size > MAX_PHOTO_BYTES:
            return response.Response(
                {"photo": f"사진 파일은 {MAX_PHOTO_BYTES // (1024 * 1024)}MB 이하만 업로드할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            Image.open(uploaded).verify()
            uploaded.seek(0)
        except (UnidentifiedImageError, OSError):
            return response.Response(
                {"photo": "올바른 사진 파일이 아닙니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Assigning over item.photo orphans the previous file, so the media
        # directory grew on every re-upload. Drop it once the new one is stored.
        previous_photo = item.photo if item.photo else None
        item.photo = uploaded
        item.save(update_fields=["photo", "updated_at"])
        if previous_photo and previous_photo.name != item.photo.name:
            previous_photo.storage.delete(previous_photo.name)
        return response.Response(
            ItemSerializer(item, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="touch-searched",
        url_name="touch-searched",
    )
    def touch_searched(self, request):
        """Mark everything matching the current search as just checked.

        This used to happen inside GET /api/items/?touch_last_checked=true. A
        read that mutates rows is unsafe to cache, prefetch or retry, so the
        write lives on its own POST route and the filters come along as query
        parameters exactly as they do for the list route.
        """
        if not request.query_params.get("q"):
            return response.Response(
                {"q": "검색어가 있어야 마지막 검색일자를 갱신할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_ids = list(self.filter_queryset(self.get_queryset()).values_list("id", flat=True))
        if not item_ids:
            return response.Response([], status=status.HTTP_200_OK)

        Item.objects.filter(owner=request.user, id__in=item_ids).update(
            last_checked_at=timezone.now(),
        )
        touched = self.base_queryset().filter(id__in=item_ids)
        return response.Response(self.get_serializer(touched, many=True).data)

    @action(detail=True, methods=["post"], url_path="touch-last-checked")
    def touch_last_checked(self, request, pk=None):
        item = self.get_object()
        item.last_checked_at = timezone.now()
        item.save(update_fields=["last_checked_at", "updated_at"])
        return response.Response(
            ItemSerializer(item, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        item = self.get_object()
        serializer = MoveItemSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        to_location_node = serializer.validated_data["to_location_node"]
        moved_at = serializer.validated_data.get("moved_at") or timezone.now()
        memo = serializer.validated_data.get("memo", "")

        history = ItemLocationHistory.objects.create(
            item=item,
            from_location_node=item.current_location_node,
            to_location_node=to_location_node,
            memo=memo,
            moved_at=moved_at,
            created_by=request.user,
        )
        item.current_location_node = to_location_node
        item.save(update_fields=["current_location_node", "updated_at"])

        return response.Response(
            {
                "item": ItemSerializer(item, context={"request": request}).data,
                "history": ItemLocationHistorySerializer(history).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        item = self.get_object()
        histories = (
            item.location_histories.select_related(
                "from_location_node",
                "to_location_node",
                "created_by",
            )
            .all()
            .order_by("-moved_at", "-id")
        )
        serializer = ItemLocationHistorySerializer(histories, many=True)
        return response.Response(serializer.data)
