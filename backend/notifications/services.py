"""Small helpers so other apps can record activity and notify users in one line."""

from .models import Activity, Notification


def log_activity(group, actor, action, description, amount=None):
    return Activity.objects.create(
        group=group, actor=actor, action=action, description=description, amount=amount
    )


def notify(recipients, kind, title, message, group=None, exclude=None):
    """Create one notification per recipient (skipping `exclude`, usually the actor)."""
    items = [
        Notification(recipient=user, kind=kind, title=title, message=message, group=group)
        for user in recipients
        if exclude is None or user.pk != exclude.pk
    ]
    Notification.objects.bulk_create(items)
    return items
