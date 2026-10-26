"""JSON endpoints for the new React app (/app/). Every query is scoped to request.user."""

from collections import Counter

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from subjects.services.spaced_repetition import due_cards

from .forms import SettingsForm
from .models import UserProfile


def _unread(user):
    return user.notifications.filter(read_at__isnull=True).count()


@ensure_csrf_cookie  # the app reads the csrftoken cookie, so make sure it exists
@api_view(['GET', 'PATCH'])
def me(request):
    """Everything the app shell needs in one call: who you are, unread count, due cards per subject.
    PATCH saves the Settings page (names, email, education level) with the same rules as the old form."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == 'PATCH':
        current = {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,
                   'education_level': profile.education_level or ''}
        form = SettingsForm({**current, **{k: v for k, v in request.data.items() if k in current}}, instance=profile)
        if not form.is_valid():
            return Response(form.errors, status=400)
        form.save()
        user.first_name, user.last_name = form.cleaned_data['first_name'], form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.save(update_fields=['first_name', 'last_name', 'email'])
    due = Counter(due_cards(user).order_by().values_list('subject_id', flat=True))
    return Response({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'education_level': profile.education_level or '',
        'education_choices': [{'value': v, 'label': label} for v, label in UserProfile.EDUCATION_LEVEL_CHOICES],
        'has_password': user.has_usable_password(),  # Google-only accounts set one instead of changing it
        'unread_notifications': _unread(user),
        'due_count': sum(due.values()),
        'subjects': [
            {'id': s.id, 'name': s.name, 'due_count': due.get(s.id, 0)}
            for s in user.subjects.order_by('name')
        ],
    })


@api_view(['GET'])
def notifications(request):
    try:
        limit = max(1, min(int(request.GET.get('limit', 50)), 50))
    except ValueError:
        raise ValidationError({'limit': 'Must be a number.'})
    items = request.user.notifications.all()[:limit]
    return Response({
        'unread': _unread(request.user),
        'results': [
            {'id': n.id, 'kind': n.kind, 'title': n.title, 'body': n.body, 'url': n.url,
             'read': n.read_at is not None, 'created_at': n.created_at}
            for n in items
        ],
    })


@api_view(['POST'])
def mark_notifications_read(request):
    """Mark the given ids read, or all unread ones when no ids are sent."""
    unread = request.user.notifications.filter(read_at__isnull=True)
    ids = request.data.get('ids')
    if ids is not None:
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            raise ValidationError({'ids': 'Must be a list of notification ids.'})
        unread = unread.filter(id__in=ids)
    return Response({'marked': unread.update(read_at=timezone.now()), 'unread': _unread(request.user)})


@api_view(['POST'])
def change_password(request):
    """Change the password (or set one, for Google-only accounts) and stay signed in."""
    form_class = PasswordChangeForm if request.user.has_usable_password() else SetPasswordForm
    form = form_class(request.user, request.data)  # runs AUTH_PASSWORD_VALIDATORS
    if not form.is_valid():
        return Response(form.errors, status=400)
    form.save()
    update_session_auth_hash(request, form.user)  # otherwise changing the password would end this session
    return Response({'ok': True})
