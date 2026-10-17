def unread_notifications(request):
    """Unread count for the nav bell."""
    if not request.user.is_authenticated:
        return {}
    return {'unread_notifications': request.user.notifications.filter(read_at__isnull=True).count()}
