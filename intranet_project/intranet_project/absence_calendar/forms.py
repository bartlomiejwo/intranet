from datetime import timedelta

from django import forms
from django.forms.widgets import TextInput
from .models import (
    Absence, AbsenceType, VacationLeave, SpecialLeave, VacationLeaveType,
    Event, RemoteWork
)
from django.contrib.auth.models import User
from company_structure.models import Employee
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

from intranet_project import general_functions


class EventCreateForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['title', 'date', 'description',]
        widgets = {
            'date': TextInput(attrs={'type': 'date'}),
        }

    def clean(self):
        validate_event_date_lte_today(self.cleaned_data.get('date'))


class EventUpdateForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['title', 'date', 'description',]
        widgets = {
            'date': TextInput(attrs={'type': 'date'}),
        }

    def clean(self):
        validate_event_date_lte_today(self.cleaned_data.get('date'))


def validate_event_date_lte_today(date):
    today = general_functions.current_date()

    if date < today:
        raise ValidationError(
            _('Event cannot be set in the past.'),
            code='event_set_in_the_past',
        )


def get_year_choices_for_vacation_leave(number_of_years_back):
    year_choices = []

    for x in range(0, number_of_years_back+1):
        year_choices.append((general_functions.current_date().year-x,
                                str(general_functions.current_date().year-x)))
    
    return year_choices


class AbsenceForm(forms.ModelForm):

    class Meta:
        model = Absence
        fields = ['absence_type', 'start_date', 'end_date', 'additional_information',]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        default_absence_type = AbsenceType.get_default_absence_type_or_none()
        if default_absence_type:
            self.fields['absence_type'].initial = default_absence_type


class AbsenceCreateForm(AbsenceForm):

    def __init__(self, *args, **kwargs):
        self.absent = kwargs.pop('absent')
        super().__init__(*args, **kwargs)

    def clean(self):
        Absence.validate_user_absence_one_at_a_time(self.absent, self.cleaned_data.get('start_date'),
                                            self.cleaned_data.get('end_date'))


class AbsenceUpdateForm(AbsenceForm):

    def __init__(self, *args, **kwargs):
        self.absence = kwargs.pop('absence')
        super().__init__(*args, **kwargs)

    def clean(self):
        Absence.validate_user_absence_one_at_a_time(self.absence.absent, self.cleaned_data.get('start_date'), 
                                            self.cleaned_data.get('end_date'), self.absence.id)


class AbsenceFinishEarlierForm(forms.ModelForm):

    class Meta:
        model = Absence
        fields = ['end_date',]

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date')
        self.end_date = kwargs.pop('end_date')
        super().__init__(*args, **kwargs)

        self.fields['end_date'] = forms.ChoiceField(
            choices=get_finish_earlier_dates_choices(self.start_date, self.end_date), label=_('End date'))


class AbsenceByManagerCreateForm(AbsenceForm):

    class Meta:
        model = Absence
        fields = ['absent', 'absence_type', 'start_date', 'end_date', 'additional_information',]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user')
        super().__init__(*args, **kwargs)

        self.fields['absent'] = forms.ModelChoiceField(
            queryset=User.objects.filter(id__in=request_user.employee.get_subordinate_users_ids()),
            label=_('Absent')
        )

        self.fields['absent'].label_from_instance = AbsenceByManagerCreateForm.absent_label_from_instance

    def clean(self):
        Absence.validate_user_absence_one_at_a_time(self.cleaned_data.get('absent'),
                self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'))

    @staticmethod
    def absent_label_from_instance(obj):
        return obj.profile.get_name()

#######################################################################
# VacationLeave
#######################################################################

class VacationLeaveForm(forms.ModelForm):

    class Meta:
        model = VacationLeave
        fields = [
            'start_date', 'end_date', 'number_of_days', 'leave_for_year', 'vacation_leave_type',
            'date_of_completion', 'decisive_person', 'message_for_decisive_person', 'absent',
        ]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
            'date_of_completion': TextInput(attrs={'type': 'date',}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_of_completion'].initial = general_functions.current_datetime().strftime(
                                                                    settings.DATE_BACKEND_FORMAT)

        default_vacation_leave_type = VacationLeaveType.get_default_vacation_leave_type_or_none()
        if default_vacation_leave_type:
            self.fields['vacation_leave_type'].initial = default_vacation_leave_type

        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            self.fields['decisive_person'] = forms.ModelChoiceField(queryset=User.objects.none(),
                                                                    label=_('Decisive person'))
        else:
            self.fields['decisive_person'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id__in=employee.get_supervisor_users_ids()),
                label=_('Decisive person')
            )

        self.fields['decisive_person'].label_from_instance = VacationLeaveForm.decisive_person_label_from_instance
        self.fields['absent'].widget = forms.HiddenInput()
        self.fields['leave_for_year'] = forms.ChoiceField(choices=get_year_choices_for_vacation_leave(3),
                                                            label=_('Leave for year'))

    @staticmethod
    def decisive_person_label_from_instance(obj):
        label = obj.profile.get_name()
        absence = obj.employee.get_todays_absence()

        if absence:
            label += ' - ' + absence.name()

            if absence.end_date == timezone.localtime(timezone.now()).date():
                label += ' (' + str(_('today')) + ')'
            else:
                label += ' ' + str(_('until')) + ' ' + absence.end_date.strftime(settings.DATE_BACKEND_FORMAT)

        return label


class VacationLeaveCreateForm(VacationLeaveForm):

    def __init__(self, *args, **kwargs):
        self.absent = kwargs.pop('absent')
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent

    def clean(self):
        VacationLeave.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        VacationLeave.validate_user_vacation_leave_one_at_a_time(self.absent, 
                        self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'))


class VacationLeaveUpdateForm(VacationLeaveForm):

    def __init__(self, *args, **kwargs):
        self.absence = kwargs.pop('absence')
        self.absent = self.absence.absent
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent

    def clean(self):
        VacationLeave.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        VacationLeave.validate_user_vacation_leave_one_at_a_time(self.absence.absent,
                        self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'), self.absence.id)


class VacationLeaveFinishEarlierForm(forms.ModelForm):

    class Meta:
        model = VacationLeave
        fields = ['pending_end_date', 'pending_number_of_days', 'message_for_decisive_person']

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date')
        self.end_date = kwargs.pop('end_date')
        super().__init__(*args, **kwargs)

        self.fields['pending_end_date'] = forms.ChoiceField(
            choices=get_finish_earlier_dates_choices(self.start_date, self.end_date), 
            label=_('End date'), required=True)
        self.fields['pending_number_of_days'].label = _('Number of days')
        self.fields['pending_number_of_days'].required = True

    def clean(self):
        dates_choices = self.fields['pending_end_date'].choices
        pending_end_date_label = self.cleaned_data.get('pending_end_date')

        for choice in dates_choices:
            if choice[1] == pending_end_date_label:
                pending_end_date = choice[0]
                break

        VacationLeave.validate_pending_number_of_days(self.start_date,
                        pending_end_date, self.cleaned_data.get('pending_number_of_days'))

#######################################################################
# SpecialLeave
#######################################################################

class SpecialLeaveForm(forms.ModelForm):

    class Meta:
        model = SpecialLeave
        fields = [
            'start_date', 'end_date', 'number_of_days', 'reason', 
            'date_of_completion', 'decisive_person', 'absent',
        ]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
            'date_of_completion': TextInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_of_completion'].initial = general_functions.current_datetime().strftime(
                                                                    settings.DATE_BACKEND_FORMAT)

        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            self.fields['decisive_person'] = forms.ModelChoiceField(queryset=User.objects.none(),
                                                                    label=_('Decisive person'))
        else:
            self.fields['decisive_person'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id__in=employee.get_supervisor_users_ids()),
                label=_('Decisive person')
            )
        
        self.fields['decisive_person'].label_from_instance = self.decisive_person_label_from_instance
        self.fields['absent'].widget = forms.HiddenInput()

    @staticmethod
    def decisive_person_label_from_instance(obj):
        label = obj.profile.get_name()
        absence = obj.employee.get_todays_absence()

        if absence:
            label += ' - ' + absence.name()

            if absence.end_date == timezone.localtime(timezone.now()).date():
                label += ' (' + str(_('today')) + ')'
            else:
                label += ' ' + str(_('until')) + ' ' + absence.end_date.strftime(settings.DATE_BACKEND_FORMAT)

        return label


class SpecialLeaveCreateForm(SpecialLeaveForm):

    def __init__(self, *args, **kwargs):
        self.absent = kwargs.pop('absent')
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent

    def clean(self):
        SpecialLeave.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        SpecialLeave.validate_user_special_leave_one_at_a_time(self.absent, 
                        self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'))


class SpecialLeaveUpdateForm(SpecialLeaveForm):

    def __init__(self, *args, **kwargs):
        self.absence = kwargs.pop('absence')
        self.absent = self.absence.absent
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent

    def clean(self):
        SpecialLeave.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        SpecialLeave.validate_user_special_leave_one_at_a_time(self.absence.absent,
                    self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'), self.absence.id)


class SpecialLeaveFinishEarlierForm(forms.ModelForm):

    class Meta:
        model = SpecialLeave
        fields = ['pending_end_date', 'pending_number_of_days', 'message_for_decisive_person',]

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date')
        self.end_date = kwargs.pop('end_date')
        super().__init__(*args, **kwargs)

        self.fields['pending_end_date'] = forms.ChoiceField(
            choices=get_finish_earlier_dates_choices(self.start_date, self.end_date),
                                                    label=_('End date'), required=True)
        self.fields['pending_number_of_days'].label = _('Number of days')
        self.fields['pending_number_of_days'].required = True

    def clean(self):
        dates_choices = self.fields['pending_end_date'].choices
        pending_end_date_label = self.cleaned_data.get('pending_end_date')

        for choice in dates_choices:
            if choice[1] == pending_end_date_label:
                pending_end_date = choice[0]
                break

        SpecialLeave.validate_pending_number_of_days(self.start_date,
                        pending_end_date, self.cleaned_data.get('pending_number_of_days'))


class SpecialLeaveUpdateConfirmationDocumentDataForm(forms.ModelForm):

    class Meta:
        model = SpecialLeave
        fields = ['confirmation_document_name', 'confirmation_document_number', 
                    'confirmation_document_issue_date',]
        widgets = {'confirmation_document_issue_date': TextInput(attrs={'type': 'date'}),}            

#######################################################################
# RemoteWork
#######################################################################

class RemoteWorkForm(forms.ModelForm):

    class Meta:
        model = RemoteWork
        fields = [
            'start_date', 'end_date', 'number_of_days', 'date_of_completion',
            'decisive_person', 'message_for_decisive_person', 'country', 'street',
            'house_number', 'apartment_number', 'postal_code', 'city', 'absent',
        ]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
            'date_of_completion': TextInput(attrs={'type': 'date',}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_of_completion'].initial = general_functions.current_datetime().strftime(
                                                                    settings.DATE_BACKEND_FORMAT)

        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            self.fields['decisive_person'] = forms.ModelChoiceField(queryset=User.objects.none(),
                                                                    label=_('Decisive person'))
        else:
            self.fields['decisive_person'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id__in=employee.get_supervisor_users_ids()),
                label=_('Decisive person')
            )

        self.fields['decisive_person'].label_from_instance = RemoteWorkForm.decisive_person_label_from_instance
        self.fields['absent'].widget = forms.HiddenInput()

    @staticmethod
    def decisive_person_label_from_instance(obj):
        label = obj.profile.get_name()
        absence = obj.employee.get_todays_absence()

        if absence:
            label += ' - ' + absence.name()

            if absence.end_date == timezone.localtime(timezone.now()).date():
                label += ' (' + str(_('today')) + ')'
            else:
                label += ' ' + str(_('until')) + ' ' + absence.end_date.strftime(settings.DATE_BACKEND_FORMAT)

        return label


class RemoteWorkCreateForm(RemoteWorkForm):

    def __init__(self, *args, **kwargs):
        self.absent = kwargs.pop('absent')
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent
        self.fields['country'].initial = _('Poland')
    
    def clean(self):
        RemoteWork.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        RemoteWork.validate_user_remote_work_one_at_a_time(self.absent, 
                        self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'))
    

class RemoteWorkUpdateForm(RemoteWorkForm):

    def __init__(self, *args, **kwargs):
        self.absence = kwargs.pop('absence')
        self.absent = self.absence.absent
        super().__init__(*args, **kwargs)
        self.fields['absent'].initial = self.absent

    def clean(self):
        RemoteWork.validate_number_of_days(self.cleaned_data.get('start_date'),
                        self.cleaned_data.get('end_date'), self.cleaned_data.get('number_of_days'))
        RemoteWork.validate_user_remote_work_one_at_a_time(self.absence.absent,
                        self.cleaned_data.get('start_date'), self.cleaned_data.get('end_date'), self.absence.id)


class RemoteWorkFinishEarlierForm(forms.ModelForm):

    class Meta:
        model = RemoteWork
        fields = ['pending_end_date', 'pending_number_of_days', 'message_for_decisive_person']

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date')
        self.end_date = kwargs.pop('end_date')
        super().__init__(*args, **kwargs)

        self.fields['pending_end_date'] = forms.ChoiceField(
            choices=get_finish_earlier_dates_choices(self.start_date, self.end_date), 
            label=_('End date'), required=True)
        self.fields['pending_number_of_days'].label = _('Number of days')
        self.fields['pending_number_of_days'].required = True

    def clean(self):
        dates_choices = self.fields['pending_end_date'].choices
        pending_end_date_label = self.cleaned_data.get('pending_end_date')

        for choice in dates_choices:
            if choice[1] == pending_end_date_label:
                pending_end_date = choice[0]
                break

        RemoteWork.validate_pending_number_of_days(self.start_date,
                        pending_end_date, self.cleaned_data.get('pending_number_of_days'))


def get_finish_earlier_dates_choices(start_date, end_date):
    choices = []
    choice_date = end_date - timedelta(days=1)

    while choice_date >= start_date:
        if choice_date < general_functions.current_date() - timedelta(days=1):
            break

        choice = (choice_date, str(choice_date))
        choices.append(choice)
        choice_date -= timedelta(days=1)
    
    return choices
