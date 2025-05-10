from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    path('dashboard/', views.learning_dashboard, name='dashboard'),
    path('course/<int:course_id>/progress/', views.update_course_progress, name='update_progress'),
    path('course/<int:course_id>/track/', views.track_course, name='track_course'),
    path('course/<int:course_id>/confirm/', views.confirm_course, name='confirm_course'),
    path('course/<int:course_id>/check-registration/', views.check_course_registration, name='check_registration'),
    path('course/<int:course_id>/detail/', views.course_detail, name='course_detail'),
    path('achievements/', views.achievements, name='achievements'),
    path('recent-activity/', views.recent_activity, name='recent_activity'),
    path('resources/', views.resource_library, name='resource_library'),
    path('resources/add/', views.add_resource, name='add_resource'),
    path('resources/<int:resource_id>/edit/', views.edit_resource, name='edit_resource'),
    path('resources/<int:resource_id>/delete/', views.delete_resource, name='delete_resource'),
]