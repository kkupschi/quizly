from rest_framework import serializers

from .models import Question, Quiz
from .utils import is_youtube_url, normalize_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    """Stellt eine einzelne Frage samt Antwortmöglichkeiten dar."""

    class Meta:
        model = Question
        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at',
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Stellt ein Quiz mit allen zugehörigen Fragen dar."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
        read_only_fields = ['video_url']


class QuizCreateSerializer(serializers.Serializer):
    """Prüft die Videoadresse, aus der ein Quiz erzeugt werden soll."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Lässt nur Youtube Adressen zu und speichert sie einheitlich."""
        if not is_youtube_url(value):
            raise serializers.ValidationError('Only YouTube URLs are supported.')
        return normalize_youtube_url(value)
