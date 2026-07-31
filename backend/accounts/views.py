from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, permissions, response, status, views

from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return response.Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return response.Response(UserSerializer(serializer.validated_data["user"]).data)


class LogoutView(views.APIView):
    def post(self, request):
        logout(request)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class MeView(views.APIView):
    def get(self, request):
        return response.Response(UserSerializer(request.user).data)


class CsrfView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return response.Response({"detail": "CSRF cookie set."})


class PasswordResetRequestView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(
            {"detail": "비밀번호 재설정 코드가 발송되었습니다."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(
            {"detail": "비밀번호가 변경되었습니다."},
            status=status.HTTP_200_OK,
        )
