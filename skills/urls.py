from django.urls import path
from . import views

app_name = 'skills'

urlpatterns = [
    # Add skills-related URLs later
    
    # Skill gap analysis
    path('gap-analysis/', views.skill_gap_analysis, name='skill_gap_analysis'),
    path('course-recommendations/', views.course_recommendations, name='course_recommendations'),
    path('courses/', views.list_courses, name='list_courses'),
    # Dream job learning path
    path('dream-job-path/', views.dream_job_path, name='dream_job_path'),
]