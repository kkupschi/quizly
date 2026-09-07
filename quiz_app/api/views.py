from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..functions import QuizGenerationError
from ..models import Quiz
from ..permissions import IsOwner
from ..utils import create_quiz_from_url
from .serializers import QuizCreateSerializer, QuizSerializer


class QuizListCreateView(generics.ListCreateAPIView):
    """Lists the own quizzes and creates new ones from a Youtube video."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Limits the list to the quizzes of the current user."""
        return Quiz.objects.filter(
            owner=self.request.user
        ).prefetch_related('questions')

    def create(self, request, *args, **kwargs):
        """Creates a quiz from the submitted video address."""
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
    """Returns, updates and deletes a single quiz."""

    serializer_class = QuizSerializer
    queryset = Quiz.objects.all().prefetch_related('questions')
    permission_classes = [IsAuthenticated, IsOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
