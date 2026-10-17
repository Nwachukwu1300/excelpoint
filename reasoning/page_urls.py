from django.urls import path

from . import pages

app_name = 'insights'

urlpatterns = [
    path('', pages.insights, name='dashboard'),
    path('<uuid:session_id>/', pages.session_debug, name='session'),
]
