from django import template
from absence_calendar.models import VacationLeave, SpecialLeave, RemoteWork


register = template.Library()


@register.simple_tag
def leaves_to_moderate(request):
    leaves_to_moderate = VacationLeave.get_number_of_vacation_leaves_to_moderate(request.user) + \
                        SpecialLeave.get_number_of_special_leaves_to_moderate(request.user) + \
                        RemoteWork.get_number_of_remote_works_to_moderate(request.user)
    
    return '99+' if leaves_to_moderate > 99 else str(leaves_to_moderate)
