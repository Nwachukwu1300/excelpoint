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
from django.views.generic import TemplateView  
from subjects.views import SubjectListView, SubjectDetailView, create_subject, upload_material, chat_fullscreen
from django.http import JsonResponse

def test_view(request, pk):
    return JsonResponse({'ok': pk})

def test_chat_view(request, pk):
    return JsonResponse({'message': f'Chat test for subject {pk}', 'working': True})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('users/', include('users.urls')),
    path('learning/', include('learning.urls')),
    path('api/', include('subjects.urls')),
    path('subjects/', SubjectListView.as_view(), name='subjects'),
    path('subjects/create/', create_subject, name='create_subject'),
    path('subjects/<int:pk>/upload/', upload_material, name='upload_material'),
    path('subjects/<int:pk>/chat/', chat_fullscreen, name='chat_fullscreen'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
