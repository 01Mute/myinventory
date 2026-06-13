from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "nickname", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "nickname", "password")
        read_only_fields = ("id",)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        email = validated_data["email"]
        username = validated_data.get("username") or self._make_username(email)
        validated_data["username"] = username
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def _make_username(self, email):
        base = email.split("@", 1)[0][:140] or "user"
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}-{suffix}"
            suffix += 1
        return username


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["identifier"]
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=password,
        )
        if user is None:
            try:
                matched_user = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                matched_user = None
            if matched_user:
                user = authenticate(
                    request=self.context.get("request"),
                    username=matched_user.username,
                    password=password,
                )

        if user is None:
            raise serializers.ValidationError("Invalid login credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        attrs["user"] = user
        return attrs
