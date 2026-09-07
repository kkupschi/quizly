from rest_framework import serializers

from ..models import Question, Quiz
from ..utils import is_youtube_url, normalize_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    """Represents a single question with its answer options."""

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
    """Represents a quiz with all of its questions."""

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
    """Validates the video address a quiz should be generated from."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Accepts Youtube addresses only and stores them in one form."""
        if not is_youtube_url(value):
            raise serializers.ValidationError(
                'Only YouTube URLs are supported.'
            )
        return normalize_youtube_url(value)
