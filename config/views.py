from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie


APP_INDEX = settings.BASE_DIR / 'static' / 'app' / 'index.html'


PUBLIC_APP_PAGES = {'/app/login', '/app/register', '/app/welcome', '/app/privacy', '/app/terms'}  # everything else in the app needs a session


@ensure_csrf_cookie
def app_shell(request):
    """Serve the built React app's index.html for every /app/ route; React Router takes it from there."""
    if not request.user.is_authenticated and request.path.rstrip('/') not in PUBLIC_APP_PAGES:
        return redirect_to_login(request.get_full_path())  # → /app/login?next=…
    try:
        return HttpResponse(APP_INDEX.read_text())
    except FileNotFoundError:
        return HttpResponse('The app is not built yet. Run: npm --prefix frontend run build',
                            status=503, content_type='text/plain')


def home(request):
    """Signed-in users go to Today in the app; everyone else to the landing page."""
    if request.user.is_authenticated:
        return redirect('app')  # the new React "Today" page replaced the old dashboard
    return redirect('/app/welcome')  # the new landing page

