"""
URL patterns for the reasoning API.

Provides the following endpoints:
- POST /api/reasoning/query/ - Run reasoning pipeline
- GET /api/reasoning/sessions/ - List sessions
- GET /api/reasoning/sessions/<uuid>/ - Get session detail
- GET /api/reasoning/sessions/<uuid>/chunks/ - Get session chunks
- GET /api/reasoning/stats/ - Get aggregate statistics
"""

from django.urls import path

from .views import (
    QueryView,
    SessionListView,
    SessionDetailView,
    SessionChunksView,
    StatsView,
)

app_name = 'reasoning'

urlpatterns = [
    # Run reasoning pipeline
    path(
        'query/',
        QueryView.as_view(),
        name='query'
    ),

    # Session management
    path(
        'sessions/',
        SessionListView.as_view(),
        name='session-list'
    ),
    path(
        'sessions/<uuid:session_id>/',
        SessionDetailView.as_view(),
        name='session-detail'
    ),
    path(
        'sessions/<uuid:session_id>/chunks/',
        SessionChunksView.as_view(),
        name='session-chunks'
    ),

    # Statistics
    path(
        'stats/',
        StatsView.as_view(),
        name='stats'
    ),
]
