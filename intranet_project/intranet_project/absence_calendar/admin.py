from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django import forms

from .models import (
        Absence, AbsenceType, VacationLeave, SpecialLeave,
        SpecialLeaveReason, SpecialLeaveConfirmationDocumentName,
        VacationLeaveType, VacationLeaveDocument, SpecialLeaveDocument,
        Event, RemoteWork, RemoteWorkDocument
    )
from intranet_project import general_functions


class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'created_by',]
    ordering = ['date', 'created_by', 'title',]
    search_fields = ['title', 'created_by', 'date',]


class AbsenceAdmin(admin.ModelAdmin):
    list_display = ['absent', 'absence_type', 'start_date', 'end_date']
    ordering = ['absent', 'absence_type', 'start_date', 'end_date']
    search_fields = ['absent__username', 'absent__first_name', 'absent__last_name',]


class VacationLeaveAdmin(admin.ModelAdmin):
    list_display = ['absent', 'date_of_completion', 'start_date', 'end_date', 'status']
    ordering = ['-date_of_completion', 'absent', 'start_date', 'end_date']
    search_fields = ['absent__username', 'absent__first_name', 'absent__last_name',]


class VacationLeaveDocumentAdmin(admin.ModelAdmin):
    list_display = ['absent_name', 'date_of_completion', 'start_date', 'end_date']
    ordering = ['-date_of_completion', 'absent_name', 'start_date', 'end_date']
    search_fields = ['absent_name', 'document_id',]
    readonly_fields = ('vacation_leave_link',)

    def vacation_leave_link(self, obj):
        has_vacation_leave = general_functions.get_related_object_or_none(obj, VacationLeave, 'vacation_leave')

        if has_vacation_leave:
            return mark_safe('<a href="{}">{}</a>'.format(
                reverse('admin:absence_calendar_vacationleave_change', args=(obj.vacation_leave.pk,)),
                str(obj.vacation_leave)
            ))
        else:
            return ''

    vacation_leave_link.short_description = _('Vacation leave')


class SpecialLeaveAdmin(admin.ModelAdmin):
    list_display = ['absent', 'date_of_completion', 'start_date', 'end_date', 'status']
    ordering = ['-date_of_completion', 'absent', 'start_date', 'end_date']
    search_fields = ['absent__username', 'absent__first_name', 'absent__last_name',]


class SpecialLeaveDocumentAdmin(admin.ModelAdmin):
    list_display = ['absent_name', 'date_of_completion', 'start_date', 'end_date',]
    ordering = ['-date_of_completion', 'absent_name', 'start_date', 'end_date']
    search_fields = ['absent_name', 'document_id',]
    readonly_fields = ('special_leave_link',)

    def special_leave_link(self, obj):
        has_special_leave = general_functions.get_related_object_or_none(obj, SpecialLeave, 'special_leave')

        if has_special_leave:
            return mark_safe('<a href="{}">{}</a>'.format(
                reverse('admin:absence_calendar_specialleave_change', args=(obj.special_leave.pk,)),
                str(obj.special_leave)
            ))
        else:
            return ''

    special_leave_link.short_description = _('Special leave')


class RemoteWorkAdmin(admin.ModelAdmin):
    list_display = ['absent', 'date_of_completion', 'start_date', 'end_date', 'status']
    ordering = ['-date_of_completion', 'absent', 'start_date', 'end_date']
    search_fields = ['absent__username', 'absent__first_name', 'absent__last_name',]


class RemoteWorkDocumentForm(forms.ModelForm):
    address_city = forms.CharField(label=_('City (remote work address)'))

    class Meta:
        model = RemoteWorkDocument
        fields = '__all__'


class RemoteWorkDocumentAdmin(admin.ModelAdmin):
    list_display = ['absent_name', 'date_of_completion', 'start_date', 'end_date']
    ordering = ['-date_of_completion', 'absent_name', 'start_date', 'end_date']
    search_fields = ['absent_name', 'document_id',]
    readonly_fields = ('remote_work_link',)
    form = RemoteWorkDocumentForm

    def remote_work_link(self, obj):
        has_remote_work = general_functions.get_related_object_or_none(obj, RemoteWork, 'remote_work')

        if has_remote_work:
            return mark_safe('<a href="{}">{}</a>'.format(
                reverse('admin:absence_calendar_remotework_change', args=(obj.remote_work.pk,)),
                str(obj.remote_work)
            ))
        else:
            return ''

    remote_work_link.short_description = _('Remote work')


admin.site.register(Event, EventAdmin)
admin.site.register(Absence, AbsenceAdmin)
admin.site.register(AbsenceType)
admin.site.register(VacationLeave, VacationLeaveAdmin)
admin.site.register(VacationLeaveDocument, VacationLeaveDocumentAdmin)
admin.site.register(VacationLeaveType)
admin.site.register(SpecialLeave, SpecialLeaveAdmin)
admin.site.register(SpecialLeaveReason)
admin.site.register(SpecialLeaveConfirmationDocumentName)
admin.site.register(SpecialLeaveDocument, SpecialLeaveDocumentAdmin)
admin.site.register(RemoteWork, RemoteWorkAdmin)
admin.site.register(RemoteWorkDocument, RemoteWorkDocumentAdmin)
