"""Sign in, register and sign out for the React app.

Plain Django views on purpose: DRF only checks CSRF for users who are already signed in, and a
login form must be CSRF-protected too (otherwise another site could sign a visitor into its account).
"""

import json
import logging

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from rest_framework.throttling import BaseThrottle

from .backends import FAIL_WINDOW
from .forms import RegistrationForm
from .tasks import send_password_reset

logger = logging.getLogger(__name__)


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


# Password reset. The request always answers the same way, so it never reveals whether an email has an account.
RESETS_PER_EMAIL, RESETS_PER_IP, RESET_WINDOW = 3, 10, 60 * 60
RESET_SENT = {'ok': True, 'detail': 'If an account uses that email, we’ve sent it a link to set a new password.'}


def _under_limit(key, limit):
    cache.add(key, 0, RESET_WINDOW)
    return cache.incr(key) <= limit


@require_POST
@csrf_protect
def password_reset(request):
    email = str(_body(request).get('email', '')).strip()
    ip = BaseThrottle().get_ident(request)
    if not email or not _under_limit(f'reset:ip:{ip}', RESETS_PER_IP) or not _under_limit(f'reset:email:{email.lower()}', RESETS_PER_EMAIL):
        return JsonResponse(RESET_SENT)  # same answer when limited: nothing to learn, nothing sent
    site = request.build_absolute_uri('/')  # scheme and host the link needs; the worker makes the token
    for user in get_user_model().objects.filter(email__iexact=email, is_active=True):
        try:
            send_password_reset.delay(user.pk, site)  # queued: sending in the request would be slower only for real accounts
        except Exception:
            logger.exception('Could not queue a password reset email')  # same answer either way
    return JsonResponse(RESET_SENT)


@require_POST
@csrf_protect
def password_reset_confirm(request):
    data = _body(request)
    try:
        user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(str(data.get('uid', '')))), is_active=True)
    except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
        user = None
    if user is None or not default_token_generator.check_token(user, str(data.get('token', ''))):
        return JsonResponse({'detail': 'This link has expired or was already used. Ask for a new one.'}, status=400)
    form = SetPasswordForm(user, {k: str(data.get(k, '')) for k in ('new_password1', 'new_password2')})
    if not form.is_valid():
        errors = dict(form.errors)
        if 'new_password2' in errors and form.data['new_password1'] == form.data['new_password2']:
            errors['new_password1'] = errors.pop('new_password2')  # "too short" is about the password itself
        return JsonResponse(errors, status=400)
    form.save()  # changes the password, which also makes this link unusable
    cache.delete(f'signin-fail:user:{user.username.lower()}')  # a fresh password ends any lockout
    login(request, user)
    return JsonResponse({'ok': True, 'next': '/app/'})
