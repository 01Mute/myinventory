from rest_framework import serializers

from .models import FloorPlan, Home


class HomeSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Home
        fields = (
            "id",
            "owner",
            "name",
            "address_optional",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def validate_name(self, value):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return value
        qs = Home.objects.filter(owner=request.user, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A home with this name already exists.")
        return value


class FloorPlanSerializer(serializers.ModelSerializer):
    home_name = serializers.CharField(source="home.name", read_only=True)

    class Meta:
        model = FloorPlan
        fields = (
            "id",
            "home",
            "home_name",
            "name",
            "width",
            "height",
            "unit",
            "background_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "home_name", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["home"].queryset = Home.objects.filter(owner=request.user)

    def validate_home(self, value):
        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError("You cannot use another user's home.")
        return value

    def validate(self, attrs):
        home = attrs.get("home", self.instance.home if self.instance else None)
        name = attrs.get("name", self.instance.name if self.instance else None)
        if home and name:
            qs = FloorPlan.objects.filter(home=home, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A floor plan with this name already exists in this home."},
                )
        return attrs
