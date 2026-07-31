from random import SystemRandom
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import serializers

from .models import PasswordResetCode


User = get_user_model()
RESET_CODE_TTL_MINUTES = 10


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

    def validate(self, attrs):
        # AUTH_PASSWORD_VALIDATORS was only being applied on password reset, so
        # a password rejected there could still be used to sign up. Run the same
        # checks here, against an unsaved user so the similarity validator works.
        candidate = User(
            username=attrs.get("username") or "",
            email=attrs.get("email", ""),
            nickname=attrs.get("nickname", ""),
        )
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return None

        PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now(),
        )
        code = f"{SystemRandom().randint(0, 999999):06d}"
        PasswordResetCode.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=timezone.now() + timezone.timedelta(minutes=RESET_CODE_TTL_MINUTES),
        )
        try:
            send_mail(
                subject="Home Inventory Map 비밀번호 재설정 코드",
                message=(
                    "비밀번호 재설정 코드입니다.\n\n"
                    f"코드: {code}\n"
                    f"유효 시간: {RESET_CODE_TTL_MINUTES}분\n\n"
                    "본인이 요청하지 않았다면 이 메일을 무시하세요."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except (OSError, SMTPException) as exc:
            raise serializers.ValidationError(
                "이메일 발송 설정을 확인하세요."
            ) from exc
        return None


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        user = self._get_user()
        if user:
            password_validation.validate_password(value, user)
        return value

    def validate(self, attrs):
        user = self._get_user()
        if not user:
            raise serializers.ValidationError("인증 코드가 올바르지 않습니다.")

        reset_code = (
            PasswordResetCode.objects.filter(user=user, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not reset_code or not reset_code.is_usable():
            raise serializers.ValidationError("인증 코드가 만료되었습니다.")

        if not check_password(attrs["code"], reset_code.code_hash):
            reset_code.attempts += 1
            reset_code.save(update_fields=("attempts",))
            raise serializers.ValidationError("인증 코드가 올바르지 않습니다.")

        attrs["user"] = user
        attrs["reset_code"] = reset_code
        return attrs

    def save(self):
        user = self.validated_data["user"]
        reset_code = self.validated_data["reset_code"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=("password",))
        reset_code.used_at = timezone.now()
        reset_code.save(update_fields=("used_at",))
        return user

    def _get_user(self):
        email = self.initial_data.get("email", "")
        return User.objects.filter(email__iexact=email, is_active=True).first()
