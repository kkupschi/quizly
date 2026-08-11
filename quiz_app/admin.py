from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.TabularInline):
    """Zeigt die Fragen eines Quiz direkt in der Quizverwaltung."""

    model = Question
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Verwaltung der Quizze samt der zugehörigen Fragen."""

    list_display = ('title', 'owner', 'created_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Verwaltung einzelner Fragen unabhängig vom Quiz."""

    list_display = ('question_title', 'quiz', 'answer')
    list_filter = ('quiz',)
    search_fields = ('question_title', 'answer')
    readonly_fields = ('created_at', 'updated_at')
