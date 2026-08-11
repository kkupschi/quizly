from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer
from .utils import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    blacklist_refresh_token,
    build_login_response,
    create_access_token,
    delete_auth_cookies,
    set_auth_cookie,
)

LOGOUT_DETAIL = (
    'Log-Out successfully! All Tokens will be deleted. '
    'Refresh token is now invalid.'
)


class RegistrationView(APIView):
    """Nimmt Registrierungen entgegen und legt neue Benutzer an."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validiert die Eingaben und erstellt den Benutzer."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Meldet den Benutzer an und setzt die Cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Prueft die Anmeldedaten und gibt die Token als Cookies zurueck."""
        user = authenticate(
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if user is None:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return build_login_response(user)


class LogoutView(APIView):
    """Meldet den Benutzer ab und macht seinen Token ungueltig."""

    def post(self, request):
        """Setzt den Token auf die Blacklist und loescht die Cookies."""
        blacklist_refresh_token(request.COOKIES.get(REFRESH_COOKIE))
        response = Response({'detail': LOGOUT_DETAIL})
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(APIView):
    """Erneuert den Zugriffstoken anhand des Cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Setzt einen neuen Zugriffstoken als Cookie."""
        access_token = create_access_token(request.COOKIES.get(REFRESH_COOKIE))
        if access_token is None:
            return Response(
                {'detail': 'Refresh token is invalid or missing.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token refreshed'})
        set_auth_cookie(response, ACCESS_COOKIE, access_token)
        return response
