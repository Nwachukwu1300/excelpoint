from django.urls import path
from . import views

urlpatterns = [
    # Resume parser views
    path('parser/', views.ResumeParserView.as_view(), name='resume_parser'),
    path('results/', views.ResumeResultsView.as_view(), name='resume_results'),
    
    # API views for skill extraction
    path('api/extract-skills/', views.SkillExtractAPIView.as_view(), name='api_extract_skills'),
    path('api/basic-extract-skills/', views.BasicSkillExtractAPIView.as_view(), name='api_basic_extract_skills'),
] 