from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

ACCESS_COOKIE = settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS']
REFRESH_COOKIE = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']


def set_auth_cookie(response, name, token):
    """Legt einen Token als Cookie auf der Response ab."""
    response.set_cookie(
        key=name,
        value=str(token),
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
    )


def build_user_payload(user):
    """Baut die Userdaten, die der Login zurückgibt."""
    return {'id': user.id, 'username': user.username, 'email': user.email}


def build_login_response(user):
    """Erstellt die Antwort für den Login inklusive gesetzter Cookies."""
    refresh = RefreshToken.for_user(user)
    response = Response({
        'detail': 'Login successfully!',
        'user': build_user_payload(user),
    })
    set_auth_cookie(response, ACCESS_COOKIE, refresh.access_token)
    set_auth_cookie(response, REFRESH_COOKIE, refresh)
    return response


def delete_auth_cookies(response):
    """Entfernt beide Cookies aus dem Browser."""
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)


def blacklist_refresh_token(raw_token):
    """Setzt den uebergebenen Token auf die Blacklist, sofern er gueltig ist."""
    if not raw_token:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        pass


def create_access_token(raw_token):
    """Erzeugt einen neuen Zugriffstoken aus dem uebergebenen Token."""
    if not raw_token:
        return None
    try:
        return RefreshToken(raw_token).access_token
    except TokenError:
        return None
