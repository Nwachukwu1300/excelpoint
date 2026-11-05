"""Email confirmation: a signed link that proves a student owns the address on their account.

The link carries the user id and the address it was sent to, so it stops working if the email changes,
and expires after a week. Nothing is stored: confirming just sets User.email_verified.
"""

import logging

from django.contrib.auth import get_user_model
from django.core import signing

logger = logging.getLogger(__name__)

SALT = 'excelpoint.confirm-email'
MAX_AGE = 7 * 24 * 60 * 60


def make_token(user):
    return signing.dumps({'u': user.pk, 'e': user.email.lower()}, salt=SALT)


def user_for_token(token):
    """The active user the link was made for, if it is genuine, unexpired and still matches their email."""
    try:
        data = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:  # also covers SignatureExpired
        return None
    user = get_user_model().objects.filter(pk=data.get('u'), is_active=True).first()
    if user is None or not user.email or user.email.lower() != data.get('e'):
        return None
    return user


def send_confirmation(user, request):
    """Queue the confirmation email; a broken queue must not fail sign-up or Settings."""
    from .tasks import send_email_confirmation
    if not user.email or user.email_verified:
        return
    try:
        send_email_confirmation.delay(user.pk, request.build_absolute_uri('/'))
    except Exception:
        logger.exception('Could not queue an email confirmation')
