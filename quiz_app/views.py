from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .functions import QuizGenerationError
from .models import Quiz
from .permissions import IsOwner
from .serializers import QuizCreateSerializer, QuizSerializer
from .utils import create_quiz_from_url


class QuizListCreateView(generics.ListCreateAPIView):
    """Listet die eigenen Quizze und erzeugt neue aus einem Youtube Video."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Beschränkt die Liste auf die Quizze des angemeldeten Users."""
        return Quiz.objects.filter(
            owner=self.request.user
        ).prefetch_related('questions')

    def create(self, request, *args, **kwargs):
        """Erzeugt ein Quiz aus der übergebenen Videoadresse."""
        input_serializer = QuizCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            quiz = create_quiz_from_url(
                request.user, input_serializer.validated_data['url']
            )
        except QuizGenerationError as error:
            return Response(
                {'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            QuizSerializer(quiz).data, status=status.HTTP_201_CREATED
        )


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Liefert, aktualisiert und löscht ein einzelnes Quiz."""

    serializer_class = QuizSerializer
    queryset = Quiz.objects.all().prefetch_related('questions')
    permission_classes = [IsAuthenticated, IsOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
