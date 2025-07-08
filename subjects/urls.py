from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'subjects', views.SubjectViewSet, basename='subject')
router.register(r'materials', views.SubjectMaterialViewSet, basename='material')
router.register(r'quiz', views.QuizViewSet, basename='quiz')

urlpatterns = [
    # Web Views
    path('', views.SubjectListView.as_view(), name='subject_list'),
    path('create/', views.create_subject, name='create_subject'),
    path('<int:pk>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    path('<int:pk>/upload/', views.upload_material, name='upload_material'),
    path('<int:pk>/material/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path('material/<int:material_id>/status/', views.material_status, name='material_status'),
    
    # Quiz URLs
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/results/<int:attempt_id>/', views.quiz_results, name='quiz_results'),
    path('quiz/attempt/<int:attempt_id>/check-questions/', views.check_dynamic_questions, name='check_dynamic_questions'),
    
    # Quiz History URLs
    path('quiz/history/', views.quiz_history, name='quiz_history'),
    path('quiz/attempt/<int:attempt_id>/detail/', views.quiz_attempt_detail, name='quiz_attempt_detail'),
] + router.urls 