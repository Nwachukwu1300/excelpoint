from django.urls import path
from django.views.generic import RedirectView

app_name = 'insights'

# The Insights pages are in the React app; old links (and chat trace_url values) land there.
urlpatterns = [
    path('', RedirectView.as_view(url='/app/insights'), name='dashboard'),
    path('<uuid:session_id>/', RedirectView.as_view(url='/app/insights/%(session_id)s'), name='session'),
]
