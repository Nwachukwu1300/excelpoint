"""Sign in, register and sign out for the React app.

Plain Django views on purpose: DRF only checks CSRF for users who are already signed in, and a
login form must be CSRF-protected too (otherwise another site could sign a visitor into its account).
"""

import json

from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .forms import RegistrationForm

# Failed sign-ins allowed per window, per username and per IP (higher: a campus network shares one address)
FAILS_PER_USER, FAILS_PER_IP, FAIL_WINDOW = 5, 20, 15 * 60


def _body(request):
    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _safe_next(request, url):
    """Only paths on this site; anything else lands on Today."""
    if url and url.startswith('/') and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()},
                                                                       require_https=request.is_secure()):
        return url
    return '/app/'


@require_POST
@csrf_protect
def sign_in(request):
    data = _body(request)
    username = str(data.get('username', '')).strip()
    # shortcut: behind a proxy REMOTE_ADDR is the proxy's address; read the client IP from it when deploying
    limits = {f'signin-fail:user:{username.lower()}': FAILS_PER_USER,
              f'signin-fail:ip:{request.META.get("REMOTE_ADDR", "")}': FAILS_PER_IP}
    # Checked before the password, so a locked account can't be unlocked by guessing right
    if any(cache.get(key, 0) >= limit for key, limit in limits.items()):
        response = JsonResponse({'detail': 'Too many failed sign-in attempts. Try again in 15 minutes.'}, status=429)
        response['Retry-After'] = str(FAIL_WINDOW)
        return response
    user = authenticate(request, username=username, password=str(data.get('password', '')))
    if user is None:
        for key in limits:
            try:
                cache.incr(key)
            except ValueError:  # first failure in this window
                cache.set(key, 1, FAIL_WINDOW)
        return JsonResponse({'detail': 'The username or password is incorrect.'}, status=400)
    cache.delete(f'signin-fail:user:{username.lower()}')
    login(request, user)
    return JsonResponse({'ok': True, 'next': _safe_next(request, data.get('next'))})


@require_POST
@csrf_protect
def register(request):
    data = _body(request)
    form = RegistrationForm({k: str(data.get(k, '')) for k in ('username', 'email', 'password1', 'password2')})
    if not form.is_valid():
        return JsonResponse(form.errors, status=400)
    user = form.save()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'next': '/app/'}, status=201)


@require_POST
@csrf_protect
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})
