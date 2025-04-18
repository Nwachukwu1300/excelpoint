from django.urls import path
from . import views

urlpatterns = [
    # Resume parser views
    path('parser/', views.ResumeParserView.as_view(), name='resume_parser'),
    path('results/', views.ResumeResultsView.as_view(), name='resume_results'),
    path('match/', views.JobSkillMatchView.as_view(), name='job_skill_match'),
    path('match/results/', views.SkillMatchResultsView.as_view(), name='skill_match_results'),
    
    # API views for skill extraction
    path('api/extract-skills/', views.SkillExtractAPIView.as_view(), name='api_extract_skills'),
] 