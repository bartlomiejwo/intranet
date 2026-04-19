from django import template
from conference_rooms.models import Meeting


register = template.Library()


@register.simple_tag
def meetings_to_moderate(user):
    number_of_meetings_to_moderate = Meeting.get_number_of_meetings_to_moderate(user)
    
    return '99+' if number_of_meetings_to_moderate > 99 else str(number_of_meetings_to_moderate)
