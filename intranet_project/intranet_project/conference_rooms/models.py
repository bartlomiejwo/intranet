from intranet_project import general_functions

from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from intranet_project import general_functions


def validate_date(date):
    today = general_functions.current_date()

    if(today > date):
        raise ValidationError(_('Meeting date cannot be set in the past.'))


class Location(models.Model):
    class Meta:
        verbose_name = _('location')
        verbose_name_plural = _('locations')

    name = models.CharField(max_length=150, unique=True, verbose_name=_('name'))
    moderator_group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL,
                                        verbose_name=_('moderator group'))
    visible = models.BooleanField(default=True, verbose_name=_('visible'))
    default = models.BooleanField(default=False, verbose_name=_('default'))

    def clean(self):
        self.validate_default()

    def validate_default(self):
        if self.default and self.visible:
            default_location = Location.get_default_location_or_none()

            if default_location and self != default_location:
                raise ValidationError(
                    _('There can be only one visible default location \
                        (current default: %(current_default)s).'),
                    code='maximum_number_of_default_visible_locations_exceeded',
                    params={'current_default': default_location}
                )
    
    @staticmethod
    def get_default_location_or_none():
        return general_functions.get_object_or_none(Location, default=True, visible=True)

    def __str__(self):
        return self.name


class ConferenceRoom(models.Model):
    class Meta:
        verbose_name = _('conference room')
        verbose_name_plural = _('conference rooms')

        constraints = [
            models.UniqueConstraint(fields=['location', 'position'], name='unique_location_position'),
        ]

    name = models.CharField(max_length=40, unique=True, verbose_name=_('name'))
    color = models.CharField(max_length=7, verbose_name=_('color'))
    position = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=_('position'))
    location = models.ForeignKey(Location, on_delete=models.RESTRICT, verbose_name=_('location'))

    def __str__(self):
        return self.name

    @staticmethod
    def get_rooms_moderated_by_user(user):
        locations = Location.objects.all()
        locations_moderated_by_user = []
        user_groups = user.groups.all()

        for location in locations:
            if location.moderator_group in user_groups:
                locations_moderated_by_user.append(location)

        return ConferenceRoom.objects.filter(location__in=locations_moderated_by_user)


class Meeting(models.Model):
    class Meta:
        verbose_name = _('meeting')
        verbose_name_plural = _('meetings')
        permissions = (('moderate_meeting', 'Can moderate meeting'), )

    PENDING_STATUS = 1
    ACCEPTED_STATUS = 2
    REJECTED_STATUS = 3

    STATUS_CHOICES = (
        (PENDING_STATUS, _('Pending')),
        (ACCEPTED_STATUS, _('Accepted')),
        (REJECTED_STATUS, _('Rejected')),
    )

    conference_room = models.ForeignKey(ConferenceRoom, on_delete=models.CASCADE, null=False, blank=False,
                                        verbose_name=_('conference room'))
    title = models.CharField(max_length=40, verbose_name=pgettext('title', 'the name of something'))
    date = models.DateField(validators=[validate_date,], verbose_name=_('date'))
    start_time = models.TimeField(verbose_name=_('start time'))
    end_time = models.TimeField(verbose_name=_('end time'))
    description = models.TextField(null=False, blank=True, verbose_name=_('description'))
    created_by = models.ForeignKey(User, related_name='Creator', on_delete=models.CASCADE, verbose_name=_('created by'))
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS, verbose_name=_('status'))
    status_changed_by = models.ForeignKey(User, related_name='Moderator', default=None,
                        on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('status changed by'))
    last_status_change_time = models.DateTimeField(default=None, null=True, blank=True,
                                                    verbose_name=_('last status change time'))
    rejection_reason = models.TextField(null=False, blank=True, verbose_name=_('rejection reason'))


    def clean(self):
        self.validate_start_end_time()

        try:
            self.validate_conference_room_availability()
        except ConferenceRoom.DoesNotExist:
            pass

    def validate_start_end_time(self):
        if self.start_time >= self.end_time:
            raise ValidationError(_('The start time must be no later than the end time.'),
                                code='start_time_later_than_end_time')

    def validate_conference_room_availability(self):
        conference_room_meetings = Meeting.objects.filter(conference_room=self.conference_room, date=self.date, 
                                                        status=Meeting.ACCEPTED_STATUS).exclude(pk=self.pk)
        colliding_meetings = self.get_colliding_meetings(conference_room_meetings)

        if len(colliding_meetings) > 0:
            raise ValidationError(
                _('At the given time meeting is already planned! %(colliding_meetings)s'),
                code='meeting_already_planned',
                params={'colliding_meetings': colliding_meetings}
            )

    def get_colliding_meetings(self, conference_room_meetings):
        colliding_meetings = []

        for meeting in conference_room_meetings:
            if not (self.end_time <= meeting.start_time or self.start_time >= meeting.end_time):
                colliding_meetings.append(f'{meeting.start_time.strftime("%H:%M")} - {meeting.end_time.strftime("%H:%M")} {meeting.title}')

        return colliding_meetings

    def can_user_moderate(self, user):
        rooms_moderated_by_user = ConferenceRoom.get_rooms_moderated_by_user(user)

        return self.conference_room in rooms_moderated_by_user

    def possible_to_edit(self):
        today = general_functions.current_date()
        now = general_functions.current_time()

        if today > self.date:
            return False

        if today == self.date:
            now = general_functions.current_time()
            
            return self.end_time >= now

        return True

    def save(self, *args, **kwargs):
        if self.status != Meeting.REJECTED_STATUS:
            self.rejection_reason = ''

        if self.status == Meeting.PENDING_STATUS:
            self.status_changed_by = None
            self.last_status_change_time = None

        super(Meeting, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    @staticmethod
    def get_number_of_meetings_to_moderate(user):
        rooms_moderated_by_user = ConferenceRoom.get_rooms_moderated_by_user(user)
        today = general_functions.current_date()
        time = general_functions.current_time()
        return Meeting.objects.filter(Q(date__gt=today) | (Q(date=today)), #& Q(start_time__gt=time)),
                                        conference_room__in=rooms_moderated_by_user,
                                        status=Meeting.PENDING_STATUS).count()


class Participant(models.Model):
    class Meta:
        verbose_name = _('participant')
        verbose_name_plural = _('participants')

    name = models.CharField(max_length=30, verbose_name=_('name'))
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, verbose_name=_('meeting'))

    def __str__(self):
        return self.name
