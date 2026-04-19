from django import template
from notifier.consumers import NotificationsConsumer
from intranet_project import general_functions
from users.models import Profile


register = template.Library()

NOTIFIER_WS_URLS_LIST = {
    'notifications': '/notifications/',
}


@register.simple_tag
def NOTIFIER_WS_URLS():
    return NOTIFIER_WS_URLS_LIST


@register.simple_tag
def NOTIFIER_REQUEST_REMOVE_NOTIFICATION():
    return NotificationsConsumer.REQUEST_REMOVE_NOTIFICATION


@register.simple_tag
def NOTIFIER_RESPONSE_PUSH_NOTIFICATION():
    return NotificationsConsumer.RESPONSE_PUSH_NOTIFICATION


@register.simple_tag
def NOTIFIER_RESPONSE_NOTIFICATION_REMOVED():
    return NotificationsConsumer.RESPONSE_NOTIFICATION_REMOVED


@register.simple_tag
def NOTIFIER_REQUEST_CHECK_NOTIFICATION():
    return NotificationsConsumer.REQUEST_CHECK_NOTIFICATION


@register.simple_tag
def NOTIFIER_RESPONSE_NOTIFICATION_CHECKED():
    return NotificationsConsumer.RESPONSE_NOTIFICATION_CHECKED


@register.simple_tag
def user_notifications(user):
    has_profile = general_functions.get_related_object_or_none(user, Profile, 'profile')
    
    if has_profile:
        return user.profile.get_notifications()
    else:
        return []


@register.filter(name='unchecked_notifications')
def unchecked_notifications(notifications):
    unchecked = 0

    for notification in notifications:
        if not notification.checked:
            unchecked += 1

    return unchecked
