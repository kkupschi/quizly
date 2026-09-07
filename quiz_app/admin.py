from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.TabularInline):
    """Shows the questions of a quiz inside the quiz admin page."""

    model = Question
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Manages quizzes together with their questions."""

    list_display = ('title', 'owner', 'created_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Manages single questions independently of their quiz."""

    list_display = ('question_title', 'quiz', 'answer')
    list_filter = ('quiz',)
    search_fields = ('question_title', 'answer')
    readonly_fields = ('created_at', 'updated_at')
