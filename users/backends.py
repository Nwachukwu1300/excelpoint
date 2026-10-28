"""Password sign-in with a cap on failed attempts. As the only auth backend, it covers every path that
checks a password: the app's sign-in, the admin login and DRF."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from rest_framework.throttling import BaseThrottle

# Failed sign-ins allowed per window, per username and per IP (higher: a campus network shares one address)
FAILS_PER_USER, FAILS_PER_IP, FAIL_WINDOW = 5, 20, 15 * 60


def _bump(key):
    cache.add(key, 0, FAIL_WINDOW)  # starts the window on the first attempt; a no-op after that
    return cache.incr(key)


class RateLimitedModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return super().authenticate(request, username, password, **kwargs)
        # The client's address, reading X-Forwarded-For only through the NUM_PROXIES trusted proxies
        ip = BaseThrottle().get_ident(request) if request is not None else ''
        # Use the stored name (sign-up treats "Sam" and "sam" as one name), and key the lockout on it too,
        # so spelling variants of one account can't each get their own allowance of guesses
        UserModel = get_user_model()
        if not UserModel.objects.filter(username=username).exists():
            username = UserModel.objects.filter(username__iexact=username).values_list('username', flat=True).first() or username
        user_key, ip_key = f'signin-fail:user:{str(username).lower()}', f'signin-fail:ip:{ip}'
        # Counted before the password is checked, so parallel guesses can't all slip under the cap,
        # and a locked account can't be unlocked by guessing right
        if _bump(user_key) > FAILS_PER_USER or _bump(ip_key) > FAILS_PER_IP:
            if request is not None:
                request.signin_locked = True
            raise PermissionDenied  # stops authenticate() without trying the password
        user = super().authenticate(request, username, password, **kwargs)
        if user is not None:
            cache.delete(user_key)
            try:
                cache.decr(ip_key)  # only failures count against the address
            except ValueError:  # the window just expired
                pass
        return user
