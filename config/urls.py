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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from subjects.views import SubjectListView, SubjectDetailView, create_subject, upload_material, review_flashcards
from .views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('users/', include('users.urls')),
    path('learning/', include('learning.urls')),
    path('api/', include('subjects.urls')),
    path('api/retrieval/', include('retrieval.urls')),  # Stage 1: Retrieval System Optimization
    path('api/reasoning/', include('reasoning.urls')),  # Stage 2: Agentic Reasoning Pipeline
    path('insights/', include('reasoning.page_urls')),  # Stage 3/4: quality dashboard + debug panel
    path('subjects/', SubjectListView.as_view(), name='subjects'),
    path('subjects/create/', create_subject, name='create_subject'),
    path('subjects/<int:pk>/upload/', upload_material, name='upload_material'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject_detail'),
    path('subjects/<int:pk>/review/', review_flashcards, name='review_flashcards'),
]

# Only serve media files locally when not using S3
if getattr(settings, 'STORAGE_BACKEND', 'local') == 'local':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
