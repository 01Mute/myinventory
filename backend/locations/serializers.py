from rest_framework import serializers

from homes.models import FloorPlan, Home
from .models import LocationNode


class LocationNodeSerializer(serializers.ModelSerializer):
    home = serializers.PrimaryKeyRelatedField(
        queryset=Home.objects.all(),
        required=False,
    )
    floor_plan = serializers.PrimaryKeyRelatedField(
        queryset=FloorPlan.objects.all(),
        required=False,
        allow_null=True,
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=LocationNode.objects.all(),
        required=False,
        allow_null=True,
    )
    home_name = serializers.CharField(source="home.name", read_only=True)
    floor_plan_name = serializers.CharField(source="floor_plan.name", read_only=True)

    class Meta:
        model = LocationNode
        fields = (
            "id",
            "home",
            "home_name",
            "floor_plan",
            "floor_plan_name",
            "parent",
            "node_type",
            "code",
            "name",
            "full_code",
            "path",
            "level",
            "geometry_json",
            "metadata_json",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "home_name",
            "floor_plan_name",
            "full_code",
            "path",
            "level",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["home"].queryset = Home.objects.filter(owner=request.user)
            self.fields["floor_plan"].queryset = FloorPlan.objects.filter(
                home__owner=request.user,
            )
            self.fields["parent"].queryset = LocationNode.objects.filter(
                home__owner=request.user,
            )

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        instance = self.instance

        parent = attrs.get("parent", instance.parent if instance else None)
        home = attrs.get("home", instance.home if instance else None)
        floor_plan = attrs.get(
            "floor_plan",
            instance.floor_plan if instance else None,
        )

        if parent and not home:
            home = parent.home
            attrs["home"] = home
        if parent and "floor_plan" not in attrs:
            floor_plan = parent.floor_plan
            attrs["floor_plan"] = floor_plan

        if not home:
            raise serializers.ValidationError({"home": "This field is required."})

        if user and home.owner_id != user.id:
            raise serializers.ValidationError("You cannot use another user's home.")
        if floor_plan and floor_plan.home_id != home.id:
            raise serializers.ValidationError(
                "Floor plan must belong to the selected home.",
            )
        if parent and parent.home_id != home.id:
            raise serializers.ValidationError(
                "Parent node must belong to the selected home.",
            )
        if (
            parent
            and floor_plan
            and parent.floor_plan_id
            and parent.floor_plan_id != floor_plan.id
        ):
            raise serializers.ValidationError(
                "Parent node must belong to the same floor plan.",
            )

        if instance and parent and parent.id == instance.id:
            raise serializers.ValidationError(
                {"parent": "A location node cannot be its own parent."},
            )

        code = attrs.get("code", instance.code if instance else None)
        if code:
            duplicates = LocationNode.objects.filter(
                home=home,
                floor_plan=floor_plan,
                parent=parent,
                code=code,
            )
            if instance:
                duplicates = duplicates.exclude(pk=instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"code": "Code must be unique under the same parent."},
                )

        return attrs


class LocationNodeTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = LocationNode
        fields = (
            "id",
            "node_type",
            "code",
            "name",
            "full_code",
            "path",
            "level",
            "geometry_json",
            "metadata_json",
            "sort_order",
            "children",
        )

    def get_children(self, obj):
        children = obj.children.all().order_by("sort_order", "name", "id")
        return LocationNodeTreeSerializer(
            children,
            many=True,
            context=self.context,
        ).data
