from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..utils import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    blacklist_refresh_token,
    build_login_response,
    create_access_token,
    delete_auth_cookies,
    set_auth_cookie,
)
from .serializers import RegistrationSerializer

LOGOUT_DETAIL = (
    'Log-Out successfully! All Tokens will be deleted. '
    'Refresh token is now invalid.'
)


class RegistrationView(APIView):
    """Accepts registrations and creates new users."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validates the input and creates the user."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Logs the user in and sets the auth cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Checks the credentials and returns the tokens as cookies."""
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
    """Logs the user out and invalidates the refresh token."""

    def post(self, request):
        """Blacklists the refresh token and clears both cookies."""
        blacklist_refresh_token(request.COOKIES.get(REFRESH_COOKIE))
        response = Response({'detail': LOGOUT_DETAIL})
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(APIView):
    """Renews the access token based on the refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Sets a new access token as a cookie."""
        access_token = create_access_token(request.COOKIES.get(REFRESH_COOKIE))
        if access_token is None:
            return Response(
                {'detail': 'Refresh token is invalid or missing.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token refreshed'})
        set_auth_cookie(response, ACCESS_COOKIE, access_token)
        return response
