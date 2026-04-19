import datetime

from django.forms import ModelForm, Select
from django.forms.widgets import TextInput
from .models import Location, ConferenceRoom, Meeting, Participant
from django.apps import apps
from django.forms.models import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, ButtonHolder, Submit
from .crispy.formset import Formset
from django.utils.translation import gettext_lazy as _

from live_settings.global_live_settings import global_live_settings


class ConferenceRoomForm(ModelForm):
    class Meta:
        model = ConferenceRoom
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'type': 'color'}),
        }


def get_hour_choices():
    hour_choices = []
    start_hour = global_live_settings.conference_rooms.start_hour
    end_hour = global_live_settings.conference_rooms.end_hour

    for hour in range(start_hour, end_hour):
        for minute in range(0, 46, 15):
            hour_choices.append((datetime.time(hour=hour, minute=minute), '{:02d}:{:02d}'.format(hour, minute)))

    hour_choices.append((datetime.time(hour=end_hour, minute=0), '{:02d}:{:02d}'.format(end_hour, 0)))

    return hour_choices


class MeetingFormAdmin(ModelForm):
    class Meta:
        model = Meeting
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(MeetingFormAdmin, self).__init__(*args, **kwargs)

        self.fields['start_time'].widget = Select(choices=get_hour_choices()[:-1])
        self.fields['end_time'].widget = Select(choices=get_hour_choices()[1:])


class MeetingForm(ModelForm):
    TYPE_CREATE = 1
    TYPE_UPDATE = 2

    class Meta:
        model = Meeting
        fields = '__all__'
        exclude = ['created_by', 'status', 'status_changed_by', 'last_status_change_time', ]
        widgets = {
            'date': TextInput(attrs={'type': 'date'}),
            }

    def __init__(self, *args, **kwargs):
        form_type = kwargs.pop('type', None)
        location = kwargs.pop('location', None)
        super(MeetingForm, self).__init__(*args, **kwargs)

        self.fields['conference_room'].queryset = ConferenceRoom.objects.filter(location=location)

        self.fields['start_time'].widget = Select(choices=get_hour_choices()[:-1])
        self.fields['end_time'].widget = Select(choices=get_hour_choices()[1:])

        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_class = 'form-vertical'
        self.helper.label_class = 'col-md-12 create-label'
        self.helper.field_class = 'col-md-12'
        self.helper.layout = Layout(
            Div(
                Field('conference_room'),
                Field('title'),
                Field('date'),
                Field('start_time'),
                Field('end_time'),
                Field('description'),
                Fieldset(_('Participants'),
                    Formset('participants')),
                ButtonHolder(
                    Submit('submit', 
                        _('Create meeting') if form_type == MeetingForm.TYPE_CREATE else _('Modify meeting'),
                        css_class='btn btn-primary')
                    ),
                )
            )


class ParticipantForm(ModelForm):

    class Meta:
        model = Participant
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(ParticipantForm, self).__init__(*args, **kwargs)


ParticipantFormSet = inlineformset_factory(
    Meeting, Participant, form=ParticipantForm, extra=1, can_delete=True
)
