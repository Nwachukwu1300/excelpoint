"""Sign in, register and sign out for the React app.

Plain Django views on purpose: DRF only checks CSRF for users who are already signed in, and a
login form must be CSRF-protected too (otherwise another site could sign a visitor into its account).
"""

import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .backends import FAIL_WINDOW
from .forms import RegistrationForm


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
    user = authenticate(request, username=str(data.get('username', '')).strip(), password=str(data.get('password', '')))
    if getattr(request, 'signin_locked', False):  # set by users.backends
        response = JsonResponse({'detail': 'Too many failed sign-in attempts. Try again in 15 minutes.'}, status=429)
        response['Retry-After'] = str(FAIL_WINDOW)
        return response
    if user is None:
        return JsonResponse({'detail': 'The username or password is incorrect.'}, status=400)
    login(request, user)
    return JsonResponse({'ok': True, 'next': _safe_next(request, data.get('next'))})


@require_POST
@csrf_protect
def register(request):
    data = _body(request)
    form = RegistrationForm({k: str(data.get(k, '')) for k in ('username', 'email', 'password1', 'password2')})
    if not form.is_valid():
        errors = dict(form.errors)
        if 'password2' in errors and form.data['password1'] == form.data['password2']:
            errors['password1'] = errors.pop('password2')  # "too short" is about the password, not the repeat of it
        return JsonResponse(errors, status=400)
    user = form.save()
    login(request, user)  # the one configured backend
    return JsonResponse({'ok': True, 'next': '/app/'}, status=201)


@require_POST
@csrf_protect
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})
