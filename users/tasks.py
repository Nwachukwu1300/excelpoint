from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_password_reset(user_id, site):
    """Sent by the worker, so the request answers just as fast whether or not the email has an account.
    The token is made here, so it never sits in the job queue."""
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return
    token = default_token_generator.make_token(user)
    link = f"{site.rstrip('/')}/app/reset-password/{urlsafe_base64_encode(force_bytes(user.pk))}/{token}"
    hours = settings.PASSWORD_RESET_TIMEOUT // 3600
    send_mail(
        'Set a new ExcelPoint password',
        f'Hello {user.username},\n\nSomeone asked to set a new password for your ExcelPoint account '
        f'(username: {user.username}). Open this link within {hours} hours:\n\n{link}\n\n'
        'If it wasn’t you, ignore this email. Your password stays the same.\n',
        None, [user.email],
    )


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_email_confirmation(user_id, site):
    """The link is made here, like the reset token, so it never sits in the job queue."""
    from .verification import MAX_AGE, make_token
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None or not user.email or user.email_verified:
        return
    link = f"{site.rstrip('/')}/app/verify-email/{make_token(user)}"
    send_mail(
        'Confirm your ExcelPoint email',
        f'Hello {user.username},\n\nPlease confirm this is your email address by opening this link within '
        f'{MAX_AGE // 86400} days:\n\n{link}\n\n'
        'Confirming lets you reset your password if you ever forget it.\n'
        'If you didn’t make an ExcelPoint account, ignore this email.\n',
        None, [user.email],
    )
