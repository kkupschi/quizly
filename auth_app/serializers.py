from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """Validiert die Registrierungsdaten und legt den Benutzer an."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Stellt sicher, dass die Mailadresse noch nicht vergeben ist."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def validate(self, attrs):
        """Prueft, ob Passwort und Passwortbestaetigung uebereinstimmen."""
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        """Erstellt den Benutzer mit gehashtem Passwort."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)
