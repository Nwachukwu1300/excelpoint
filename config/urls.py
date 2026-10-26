"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from subjects.views import create_subject, upload_material
from subjects import app_api as subjects_app_api, quiz_api
from reasoning import app_api as reasoning_app_api
from users import api as users_api
from .views import home, app_shell

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    re_path(r'^app(?:/.*)?$', app_shell, name='app'),  # the new React app; its router handles the rest
    path('users/', include('users.urls')),
    path('learning/', include('learning.urls')),
    path('api/me/', users_api.me, name='api_me'),
    path('api/me/password/', users_api.change_password, name='api_change_password'),
    path('api/home/', subjects_app_api.home, name='api_home'),
    path('api/review/queue/', subjects_app_api.review_queue, name='api_review_queue'),
    path('api/review/grade/', subjects_app_api.review_grade, name='api_review_grade'),
    path('api/quiz/<int:quiz_id>/attempts/', quiz_api.start_attempt, name='api_quiz_start'),
    path('api/quiz/attempts/', quiz_api.history, name='api_quiz_history'),
    path('api/quiz/attempts/<int:attempt_id>/', quiz_api.attempt_detail, name='api_quiz_attempt'),
    path('api/quiz/attempts/<int:attempt_id>/submit/', quiz_api.submit_attempt, name='api_quiz_submit'),
    path('api/quiz/attempts/<int:attempt_id>/results/', quiz_api.attempt_results, name='api_quiz_results'),
    path('api/notifications/', users_api.notifications, name='api_notifications'),
    path('api/notifications/read/', users_api.mark_notifications_read, name='api_notifications_read'),
    path('api/', include('subjects.urls')),
    path('api/retrieval/', include('retrieval.urls')),  # Stage 1: Retrieval System Optimization
    path('api/reasoning/insights/', reasoning_app_api.insights, name='api_insights'),
    path('api/reasoning/sessions/<uuid:session_id>/trace/', reasoning_app_api.trace, name='api_trace'),
    path('api/reasoning/', include('reasoning.urls')),  # Stage 2: Agentic Reasoning Pipeline
    path('insights/', include('reasoning.page_urls')),  # Stage 3/4: quality dashboard + debug panel
    path('subjects/', RedirectView.as_view(url='/app/subjects'), name='subjects'),  # rebuilt in the React app
    path('subjects/create/', create_subject, name='create_subject'),
    path('subjects/<int:pk>/upload/', upload_material, name='upload_material'),
    path('subjects/<int:pk>/', RedirectView.as_view(url='/app/subjects/%(pk)s'), name='subject_detail'),  # workspace + XP chat now in the app
    path('subjects/<int:pk>/review/', RedirectView.as_view(url='/app/review?subject=%(pk)s'), name='review_flashcards'),  # review is in the app
]

# Only serve media files locally when not using S3
if getattr(settings, 'STORAGE_BACKEND', 'local') == 'local':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
