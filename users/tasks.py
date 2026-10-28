from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_password_reset(user_id, link):
    """Sent by the worker, so the request answers just as fast whether or not the email has an account."""
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return
    hours = settings.PASSWORD_RESET_TIMEOUT // 3600
    send_mail(
        'Set a new ExcelPoint password',
        f'Hello {user.username},\n\nSomeone asked to set a new password for your ExcelPoint account '
        f'(username: {user.username}). Open this link within {hours} hours:\n\n{link}\n\n'
        'If it wasn’t you, ignore this email. Your password stays the same.\n',
        None, [user.email],
    )
