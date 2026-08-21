from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authentifiziert Requests über den Token im Cookie."""

    def authenticate(self, request):
        """Liest den Token aus dem Cookie und gibt den User zurück."""
        cookie_name = settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS']
        raw_token = request.COOKIES.get(cookie_name)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
