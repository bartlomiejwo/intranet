from urllib import parse

from django import template
from django.conf import settings
from django.utils.html import mark_safe

from live_settings.global_live_settings import global_live_settings
from live_settings.models import UsefulLink


register = template.Library()


@register.simple_tag
def date_input_format():
    return settings.DATE_FRONTEND_FORMAT_FOR_BACKEND


@register.simple_tag
def datetime_input_format():
    return settings.DATETIME_FRONTEND_FORMAT_FOR_BACKEND


@register.simple_tag
def language_code():
    return settings.LANGUAGE_CODE


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()

    for kwarg in kwargs:
        try:
            query.pop(kwarg)
        except KeyError:
            pass

    query.update(kwargs)
    return mark_safe(query.urlencode())


@register.simple_tag
def website_name():
    return global_live_settings.general.website_name


@register.simple_tag
def logo_url():
    return global_live_settings.general.logo.url


@register.simple_tag
def user_liked_object(user, obj):
    return obj.user_liked(user)


@register.simple_tag
def useful_links():
    return UsefulLink.objects.all().order_by('position')
