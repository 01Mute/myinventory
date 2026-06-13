from django.utils import timezone
from rest_framework import serializers

from locations.models import LocationNode
from .models import Category, Item, ItemLocationHistory, Tag


class CategorySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "owner", "name", "created_at", "updated_at")
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return value
        qs = Category.objects.filter(owner=request.user, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value


class TagSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Tag
        fields = ("id", "owner", "name", "created_at")
        read_only_fields = ("id", "owner", "created_at")

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return value
        qs = Tag.objects.filter(owner=request.user, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A tag with this name already exists.")
        return value


class ItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )
    current_location_node = serializers.PrimaryKeyRelatedField(
        queryset=LocationNode.objects.all(),
        required=False,
        allow_null=True,
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        many=True,
        required=False,
        write_only=True,
    )
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    location_code = serializers.CharField(
        source="current_location_node.full_code",
        read_only=True,
    )
    location_path = serializers.CharField(
        source="current_location_node.path",
        read_only=True,
    )

    class Meta:
        model = Item
        fields = (
            "id",
            "owner",
            "name",
            "category",
            "category_name",
            "description",
            "quantity",
            "current_location_node",
            "location_code",
            "location_path",
            "photo",
            "purchase_price",
            "purchase_date",
            "status",
            "last_checked_at",
            "tags",
            "tag_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "category_name",
            "location_code",
            "location_path",
            "tags",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["category"].queryset = Category.objects.filter(
                owner=request.user,
            )
            self.fields["current_location_node"].queryset = LocationNode.objects.filter(
                home__owner=request.user,
            )
            self.fields["tag_ids"].queryset = Tag.objects.filter(owner=request.user)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        category = attrs.get("category")
        location_node = attrs.get("current_location_node")
        tags = attrs.get("tags", [])

        if user and category and category.owner_id != user.id:
            raise serializers.ValidationError("You cannot use another user's category.")
        if user and location_node and location_node.home.owner_id != user.id:
            raise serializers.ValidationError("You cannot use another user's location.")
        if user and any(tag.owner_id != user.id for tag in tags):
            raise serializers.ValidationError("You cannot use another user's tag.")
        return attrs

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        item = Item.objects.create(owner=self.context["request"].user, **validated_data)
        item.tags.set(tags)
        return item

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        item = super().update(instance, validated_data)
        if tags is not None:
            item.tags.set(tags)
        return item


class MoveItemSerializer(serializers.Serializer):
    to_location_node = serializers.PrimaryKeyRelatedField(
        queryset=LocationNode.objects.all(),
    )
    memo = serializers.CharField(max_length=255, required=False, allow_blank=True)
    moved_at = serializers.DateTimeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["to_location_node"].queryset = LocationNode.objects.filter(
                home__owner=request.user,
            )

    def validate_to_location_node(self, value):
        request = self.context.get("request")
        if request and value.home.owner_id != request.user.id:
            raise serializers.ValidationError("You cannot use another user's location.")
        return value

    def validate_moved_at(self, value):
        return value or timezone.now()


class ItemLocationHistorySerializer(serializers.ModelSerializer):
    from_location_code = serializers.CharField(
        source="from_location_node.full_code",
        read_only=True,
    )
    from_location_path = serializers.CharField(
        source="from_location_node.path",
        read_only=True,
    )
    to_location_code = serializers.CharField(
        source="to_location_node.full_code",
        read_only=True,
    )
    to_location_path = serializers.CharField(
        source="to_location_node.path",
        read_only=True,
    )

    class Meta:
        model = ItemLocationHistory
        fields = (
            "id",
            "item",
            "from_location_node",
            "from_location_code",
            "from_location_path",
            "to_location_node",
            "to_location_code",
            "to_location_path",
            "memo",
            "moved_at",
            "created_by",
            "created_at",
        )
        read_only_fields = fields
