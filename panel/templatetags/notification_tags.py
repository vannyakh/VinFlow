from django import template

register = template.Library()

@register.filter
def unread(notifications):
    """Filter notifications to return only unread ones"""
    if notifications is None:
        return []
    # Handle both querysets and lists
    try:
        # If it's a queryset, filter it
        if hasattr(notifications, 'filter'):
            return notifications.filter(is_read=False)
        # Otherwise, it's a list/iterable
        return [n for n in notifications if not n.is_read]
    except (AttributeError, TypeError):
        return []

