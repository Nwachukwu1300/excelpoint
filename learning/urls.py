from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    path('dashboard/', views.learning_dashboard, name='dashboard'),
    path('course/<int:course_id>/progress/', views.update_course_progress, name='update_progress'),
    path('course/<int:course_id>/track/', views.track_course, name='track_course'),
    path('achievements/', views.achievements, name='achievements'),
]