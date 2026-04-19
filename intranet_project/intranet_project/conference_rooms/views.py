from datetime import datetime, timedelta
import json

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from .models import ConferenceRoom, Meeting, Location
from django.apps import apps
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError

from intranet_project import general_functions
from .forms import MeetingForm, ParticipantFormSet
from . import signals
from live_settings.global_live_settings import global_live_settings


class UpcomingMeetingsListView(ListView):
    model = Meeting
    template_name = 'conference_rooms/upcoming_meetings.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        today = general_functions.current_date()
        time = general_functions.current_time()
        upcoming_meetings = Meeting.objects.filter(Q(date__gt=today) | (Q(date=today) & Q(start_time__gt=time)), 
                                                    status=Meeting.ACCEPTED_STATUS).order_by('date', 
                                                    'conference_room', 'start_time', 'end_time')
        return upcoming_meetings


def conference_rooms_pdf(request, date_str):
    location = request.GET.get('location', None)

    if not location:
        location = Location.get_default_location_or_none()

    context = get_conference_rooms_context(date_str, location)
    context['SCHEME'] = request.scheme
    context['HTTP_HOST'] = request.META['HTTP_HOST']

    options = {
        'page-size': 'A4',
        'dpi': 400,
        'orientation': 'landscape',
        'javascript-delay': '1000',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    template_path = 'conference_rooms/conference_rooms_pdf.html'
    filename = f'{_("Conference rooms")} - {date_str}'

    return general_functions.get_pdf_response(options, context, template_path, filename)


def conference_room_pdf(request, room_id, date_str):
    context = get_conference_rooms_context(date_str, None, room_id)
    context['SCHEME'] = request.scheme
    context['HTTP_HOST'] = request.META['HTTP_HOST']
    
    options = {
        'page-size': 'A4',
        'dpi': 400,
        'orientation': 'landscape',
        'javascript-delay': '1000',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    template_path = 'conference_rooms/conference_rooms_pdf.html'
    filename = f'{_("Conference rooms")} - {date_str}'

    return general_functions.get_pdf_response(options, context, template_path, filename)


class MeetingDetailView(UserPassesTestMixin, DetailView):
    model = Meeting
    template_name = 'conference_rooms/meeting_detail.html'

    def get_context_data(self, **kwargs):
        statuses = {
            'PENDING': Meeting.PENDING_STATUS,
            'ACCEPTED': Meeting.ACCEPTED_STATUS,
            'REJECTED': Meeting.REJECTED_STATUS,
        }

        context = super(MeetingDetailView, self).get_context_data(**kwargs)
        context['status'] = Meeting.ACCEPTED_STATUS
        context['statuses'] = statuses

        return context

    def test_func(self):
        meeting = self.get_object()

        if meeting.status == Meeting.ACCEPTED_STATUS:
            return True
        elif self.request.user.groups.filter(name=settings.GROUP_INTRANET_MEETINGS_MODERATORS).exists():
            return True
        else:
            return self.request.user == meeting.created_by


class MeetingCreateView(LoginRequiredMixin, CreateView):
    model = Meeting
    template_name = 'conference_rooms/meeting_create.html'
    form_class = MeetingForm

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['type'] = MeetingForm.TYPE_CREATE

        location = self.request.GET.get('location', None)

        if not location:
            location = Location.get_default_location_or_none()
        
        form_kwargs['location'] = location

        return form_kwargs

    def get_context_data(self, **kwargs):
        data = super(MeetingCreateView, self).get_context_data(**kwargs)
        data['locations'] = Location.objects.all().order_by('-default', 'name')

        if self.request.POST:
            data['participants'] = ParticipantFormSet(self.request.POST)
        else:
            data['participants'] = ParticipantFormSet(initial=[{'name': self.request.user.profile.get_name(),}])

        return data
    
    def form_valid(self, form):
        context = self.get_context_data()
        participants = context['participants']

        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()

            if participants.is_valid():
                participants.instance = self.object
                participants.save()

        if self.object.can_user_moderate(self.object.created_by):
            self.object.status = Meeting.ACCEPTED_STATUS
            self.object.status_changed_by = self.object.created_by
            self.object.last_status_change_time = general_functions.current_datetime()
        else:
            signals.meeting_pending.send(sender=Meeting, instance=self.object)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('conference_rooms:meeting_detail', kwargs={'pk': self.object.pk})


class MeetingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Meeting
    template_name = 'conference_rooms/meeting_update.html'
    form_class = MeetingForm

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['type'] = MeetingForm.TYPE_UPDATE

        location = self.request.GET.get('location', None)

        if not location:
            location = self.object.conference_room.location
        
        form_kwargs['location'] = location

        return form_kwargs

    def get_context_data(self, **kwargs):
        data = super(MeetingUpdateView, self).get_context_data(**kwargs)
        data['locations'] = Location.objects.all().order_by('-default', 'name')

        if self.request.POST:
            data['participants'] = ParticipantFormSet(self.request.POST, instance=self.object)
        else:
            data['participants'] = ParticipantFormSet(instance=self.object)

        return data
    
    def form_valid(self, form):
        context = self.get_context_data()
        participants = context['participants']
        was_accepted = True if self.object.status == Meeting.ACCEPTED_STATUS else False

        with transaction.atomic():
            form.instance.status = Meeting.PENDING_STATUS
            form.instance.status_changed_by = self.request.user
            form.instance.last_status_change_time = general_functions.current_datetime()
            self.object = form.save()

            if participants.is_valid():
                participants.instance = self.object
                participants.save()
        
        if was_accepted:
            if self.object.can_user_moderate(self.object.created_by):
                self.object.status = Meeting.ACCEPTED_STATUS
                self.object.status_changed_by = self.object.created_by
                self.object.last_status_change_time = general_functions.current_datetime()
            else:
                signals.accepted_meeting_updated.send(sender=Meeting, instance=self.object)
            
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('conference_rooms:meeting_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        meeting = self.get_object()

        return self.request.user == meeting.created_by


class MeetingDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Meeting
    template_name = 'conference_rooms/meeting_confirm_delete.html'
    success_url = '/'

    def delete(self, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status == Meeting.ACCEPTED_STATUS:
            if not self.object.can_user_moderate(self.object.created_by):
                signals.accepted_meeting_deleted.send(sender=Meeting, instance=self.object)
        
        return super(MeetingDeleteView, self).delete(*args, **kwargs)

    def test_func(self):
        meeting = self.get_object()

        return self.request.user == meeting.created_by


def conference_rooms(request, date_str):
    location = request.GET.get('location', None)

    if not location:
        location = Location.get_default_location_or_none()

    context = get_conference_rooms_context(date_str, location)

    return render(request, 'conference_rooms/conference_rooms.html', context)


def conference_room(request, date_str, room_id):
    context = get_conference_rooms_context(date_str, None, room_id)

    return render(request, 'conference_rooms/conference_room.html', context)


def get_conference_rooms_context(date_str, location_id, room_id=None):
    date = general_functions.validated_date(date_str)
    start_hour = global_live_settings.conference_rooms.start_hour
    end_hour = global_live_settings.conference_rooms.end_hour

    conference_rooms = get_conference_rooms_data(date, location_id, room_id)
    header_hours = generate_header_hours(start_hour, end_hour-1)
    table = create_table(header_hours, len(conference_rooms))

    prepare_time_indexes(conference_rooms, start_hour, end_hour)
    fill_table_data(table, conference_rooms)

    previous_date = date - timedelta(days=1)
    next_date = date + timedelta(days=1)

    context = {
        'table_headers': [{'name': x['name'], 'id': x['id']} for x in conference_rooms],
        'table': table,
        'previous_date': previous_date.strftime(settings.DATE_BACKEND_FORMAT),
        'display_date': date_str,
        'next_date': next_date.strftime(settings.DATE_BACKEND_FORMAT),
        'locations': Location.objects.all().order_by('-default', 'name'),
        }

    if date == general_functions.current_date():
        context['current_time_index'] = get_time_index(general_functions.current_datetime(), start_hour, end_hour)
        context['ms_until_time_indicator_move'] = get_next_time_indicator_move()

    return context


def get_conference_rooms_data(date, location_id, room_id=None):
    if room_id:
        conference_rooms = ConferenceRoom.objects.filter(id=room_id)
    else:
        conference_rooms = ConferenceRoom.objects.filter(location_id=location_id).order_by('position')
    conference_rooms_data = []
        
    for conference_room in conference_rooms:
        conference_room_data = {
            'id': conference_room.id,
            'name': conference_room.name,
            'color': conference_room.color,
            'meetings': []
        }
        meetings = Meeting.objects.filter(conference_room=conference_room.pk, status=Meeting.ACCEPTED_STATUS, 
                                          date=date).order_by('start_time')

        for meeting in meetings:
            conference_room_data['meetings'].append({
                'id': meeting.id,
                'start_time': meeting.start_time.strftime('%H:%M'), 
                'end_time': meeting.end_time.strftime('%H:%M'),
                'title': meeting.title, 
                'description': meeting.description,
                'participants': [x.name for x in meeting.participant_set.all().order_by('name')],
            })
        
        conference_rooms_data.append(conference_room_data)

    desired_rooms_number = global_live_settings.conference_rooms.desired_rooms_number

    if len(conference_rooms_data) > desired_rooms_number:
        conference_rooms_data = get_adjusted_rooms_data(conference_rooms_data, desired_rooms_number)

    return conference_rooms_data


def get_adjusted_rooms_data(conference_rooms_data, desired_rooms_number):
    indexes_to_remove = []

    for i in range(len(conference_rooms_data)-1, -1, -1):
        if len(conference_rooms_data) - len(indexes_to_remove) <= desired_rooms_number:
            break

        if len(conference_rooms_data[i]['meetings']) == 0:
            indexes_to_remove.append(i)

    return [room_data for i, room_data in enumerate(conference_rooms_data) if i not in indexes_to_remove]


def generate_header_hours(start_hour, end_hour):
    hours = []

    for hour in range(start_hour, end_hour+1):
        hours.append('{:02d}:00'.format(hour))

    return hours


def create_table(hours, conference_rooms_number):
    table = []

    for hour in hours:
        for i in range(0, 4):
            row = {'header': None, 'cells': []}

            if i%4 == 0:
                row['header'] = hour
                
            for room_index in range(0, conference_rooms_number):
                cell = {'active': True,}
                row['cells'].append(cell)
            table.append(row)
    
    return table


def prepare_time_indexes(rooms, start_hour, end_hour):
    hours_map = generate_hours_map(start_hour, end_hour)

    for room in rooms:
        for meeting in room['meetings']:
            map_meetings_times_to_index(meeting, hours_map[:-1], 'start_time', 'start_index')
            map_meetings_times_to_index(meeting, hours_map[1:], 'end_time', 'end_index')


def generate_hours_map(start_hour, end_hour):
    hours = []

    for hour in range(start_hour, end_hour):
        for minute in range(0, 46, 15):
            hours.append('{:02d}:{:02d}'.format(hour, minute))
    hours.append('{:02d}:{:02d}'.format(end_hour, 0))

    return hours


def map_meetings_times_to_index(meeting, hours, key_time, key_index):
    index = 0

    for hour in hours:
        if meeting[key_time] == hour:
            meeting[key_index] = index
            break

        index += 1


def map_hour_to_index(hour, hours_map):
    index = 0

    for hour_map in hours_map:
        if hour == hour_map:
            return index

        index += 1
    
    return None


def fill_table_data(table, rooms):
    cell = 0

    for room in rooms:
        for meeting in room['meetings']:
            table[meeting['start_index']]['cells'][cell]['reserved'] = True
            table[meeting['start_index']]['cells'][cell]['rowspan'] = 1 + meeting['end_index'] - meeting['start_index']
            table[meeting['start_index']]['cells'][cell]['color'] = room['color']
            table[meeting['start_index']]['cells'][cell]['meeting_id'] = meeting['id']
            table[meeting['start_index']]['cells'][cell]['time'] = f'{meeting["start_time"]}-{meeting["end_time"]}'
            table[meeting['start_index']]['cells'][cell]['title'] = meeting['title']

            if table[meeting['start_index']]['cells'][cell]['rowspan'] >= 4:
                table[meeting['start_index']]['cells'][cell]['participants'] = meeting['participants']
            if table[meeting['start_index']]['cells'][cell]['rowspan'] >= 5:
                table[meeting['start_index']]['cells'][cell]['description'] = meeting['description']
            

            for x in range(meeting['start_index']+1, meeting['end_index']+1):
                table[x]['cells'][cell] = {}

        cell += 1


def normalize_time(time, up):
    hour = time.hour
    minute = time.minute

    if minute < 15:
        minute = 15 if up else 0
    elif minute < 30:
        minute = 30 if up else 15
    elif minute < 45:
        minute = 45 if up else 30
    elif up:
        minute = 0
        hour += 1

        if hour > 23:
            hour = 0
    else:
        minute = 45

    return '{:02d}:{:02d}'.format(hour, minute)


def get_time_index(time, start_hour, end_hour):
    hours_map = generate_hours_map(start_hour, end_hour)
    normalized_time = normalize_time(time, up=False)

    return map_hour_to_index(normalized_time, hours_map[:-1])


def get_next_time_indicator_move():
    now = general_functions.current_datetime()
    normalized_now = normalize_time(now, up=True)

    colon_position = normalized_now.index(':')
    next_move_time = datetime(now.year, now.month, now.day, int(normalized_now[:colon_position]),
                            int(normalized_now[colon_position+1:]), 0)

    return int((next_move_time.timestamp() - now.timestamp()) * 1000)


class MeetingsModerationListView(PermissionRequiredMixin, ListView):
    permission_required = 'conference_rooms.moderate_meeting'
    model = Meeting
    template_name = 'conference_rooms/meetings_moderation.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        rooms_moderated_by_user = ConferenceRoom.get_rooms_moderated_by_user(self.request.user)
        today = general_functions.current_date()
        time = general_functions.current_time()
        meetings_to_moderate = Meeting.objects.filter(Q(date__gt=today) | (Q(date=today)), #& Q(start_time__gt=time)),
                                                    status=Meeting.PENDING_STATUS,
                                                    conference_room__in=rooms_moderated_by_user).order_by('date',
                                                    'conference_room', 'start_time', 'end_time')
        return meetings_to_moderate


class MeetingAcceptView(PermissionRequiredMixin, View):
    permission_required = 'conference_rooms.moderate_meeting'

    def post(self, request, id):
        meeting = get_object_or_404(Meeting, id=id)

        if not meeting.can_user_moderate(request.user):
            return JsonResponse({'message': 
                _('You are not allowed to accept this meeting.'),}, status=403)

        if meeting.status != Meeting.PENDING_STATUS:
            return JsonResponse({'message': 
                _('The decision on this meeting has already been made.'),}, status=405)

        meeting.status = Meeting.ACCEPTED_STATUS
        meeting.status_changed_by = request.user
        meeting.last_status_change_time = general_functions.current_datetime()
        context = get_meeting_status_change_context(meeting, _('The meeting was accepted.'))

        if context['ok']:
            signals.meeting_accepted.send(sender=Meeting, instance=meeting)

        return JsonResponse(context, status=200)


class MeetingRejectView(PermissionRequiredMixin, View):
    permission_required = 'conference_rooms.moderate_meeting'

    def post(self, request, id):
        meeting = get_object_or_404(Meeting, id=id)

        if not meeting.can_user_moderate(request.user):
            return JsonResponse({'message': 
                _('You are not allowed to reject this meeting.'),}, status=403)

        if meeting.status != Meeting.PENDING_STATUS:
            return JsonResponse({'message': 
                _('The decision on this meeting has already been made.'),}, status=405)

        meeting.status = Meeting.REJECTED_STATUS
        meeting.status_changed_by = request.user
        meeting.last_status_change_time = general_functions.current_datetime()
        meeting.rejection_reason = request.POST['reason']
        context = get_meeting_status_change_context(meeting, _('The meeting was rejected.'))

        if context['ok']:
            signals.meeting_rejected.send(sender=Meeting, instance=meeting)

        return JsonResponse(context, status=200)


def get_meeting_status_change_context(meeting, message):
    try:
        meeting.full_clean()
    except ValidationError as e:
        response_message = f'{_("Validation error occured")}: {str(e)}'
        response_state = False
    else:
        meeting.save()
        response_message = message
        response_state = True

    context = {
        'ok': response_state,
        'message': response_message,
    }

    return context


class UserAcceptedMeetingsListView(LoginRequiredMixin, ListView):
    model = Meeting
    template_name = 'conference_rooms/user_meetings.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        args = []
        kwargs = {}

        fill_user_meetings_query_args(self.request, args, kwargs)

        meetings = Meeting.objects.filter(
                    created_by=self.request.user,
                    status=Meeting.ACCEPTED_STATUS,
                    *args, **kwargs
                    ).order_by('-date', 'conference_room', 'start_time', 'end_time')

        return meetings

    def get_context_data(self, **kwargs):
        statuses = {
            'PENDING': Meeting.PENDING_STATUS,
            'ACCEPTED': Meeting.ACCEPTED_STATUS,
            'REJECTED': Meeting.REJECTED_STATUS,
        }

        context = super(UserAcceptedMeetingsListView, self).get_context_data(**kwargs)
        context['status'] = Meeting.ACCEPTED_STATUS
        context['statuses'] = statuses
        context['conference_rooms'] = ConferenceRoom.objects.all().order_by('location', 'name')

        return context


class UserPendingMeetingsListView(LoginRequiredMixin, ListView):
    model = Meeting
    template_name = 'conference_rooms/user_meetings.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        args = []
        kwargs = {}

        fill_user_meetings_query_args(self.request, args, kwargs)

        meetings = Meeting.objects.filter(
                            created_by=self.request.user,
                            status=Meeting.PENDING_STATUS,
                            *args, **kwargs
                            ).order_by('-date', 'conference_room', 'start_time', 'end_time')
        return meetings

    def get_context_data(self, **kwargs):
        statuses = {
            'PENDING': Meeting.PENDING_STATUS,
            'ACCEPTED': Meeting.ACCEPTED_STATUS,
            'REJECTED': Meeting.REJECTED_STATUS,
        }

        context = super(UserPendingMeetingsListView, self).get_context_data(**kwargs)
        context['status'] = Meeting.PENDING_STATUS
        context['statuses'] = statuses
        context['conference_rooms'] = ConferenceRoom.objects.all().order_by('location', 'name')

        return context


class UserRejectedMeetingsListView(LoginRequiredMixin, ListView):
    model = Meeting
    template_name = 'conference_rooms/user_meetings.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        args = []
        kwargs = {}

        fill_user_meetings_query_args(self.request, args, kwargs)

        meetings = Meeting.objects.filter(
                            created_by=self.request.user,
                            status=Meeting.REJECTED_STATUS,
                            *args, **kwargs
                            ).order_by('-date', 'conference_room', 'start_time', 'end_time')
        return meetings

    def get_context_data(self, **kwargs):
        statuses = {
            'PENDING': Meeting.PENDING_STATUS,
            'ACCEPTED': Meeting.ACCEPTED_STATUS,
            'REJECTED': Meeting.REJECTED_STATUS,
        }

        context = super(UserRejectedMeetingsListView, self).get_context_data(**kwargs)
        context['status'] = Meeting.REJECTED_STATUS
        context['statuses'] = statuses
        context['conference_rooms'] = ConferenceRoom.objects.all().order_by('location', 'name')

        return context


def fill_user_meetings_query_args(request, args, kwargs):
    if request.GET.get('conferenceRoom', None) is not None:
        try:
            kwargs['conference_room__id'] = int(request.GET.get('conferenceRoom'))
        except ValueError:
            pass

    if request.GET.get('meetingTitle', None) is not None:
        kwargs['title__icontains'] = request.GET.get('meetingTitle', '')

    if request.GET.get('meetingRangeDateStart', None) is not None:
        general_functions.fill_date_kwarg(kwargs, 'date__gte', request.GET['meetingRangeDateStart'])

    if request.GET.get('meetingRangeDateEnd', None) is not None:
        general_functions.fill_date_kwarg(kwargs, 'date__lte', request.GET['meetingRangeDateEnd'])


class MeetingsModerationHistoryListView(PermissionRequiredMixin, ListView):
    permission_required = 'conference_rooms.moderate_meeting'
    model = Meeting
    template_name = 'conference_rooms/meetings_moderation_history.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        args = []
        kwargs = {}

        self.fill_query_args(args, kwargs)

        rooms_moderated_by_user = ConferenceRoom.get_rooms_moderated_by_user(self.request.user)
        processed_meetings = Meeting.objects.filter(
                                    ~Q(status=Meeting.PENDING_STATUS),
                                    conference_room__in=rooms_moderated_by_user,
                                    *args, **kwargs
                                    ).order_by('-date', 'conference_room', 'start_time', 'end_time')

        return processed_meetings

    def get_context_data(self, **kwargs):
        statuses = {
            'PENDING': Meeting.PENDING_STATUS,
            'ACCEPTED': Meeting.ACCEPTED_STATUS,
            'REJECTED': Meeting.REJECTED_STATUS,
        }

        context = super(MeetingsModerationHistoryListView, self).get_context_data(**kwargs)
        context['statuses'] = statuses
        context['conference_rooms'] = ConferenceRoom.objects.all().order_by('location', 'name')

        return context
        
    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('meetingOrganizerFirstName', None) is not None or \
            self.request.GET.get('meetingOrganizerLastName', None) is not None:
            kwargs['created_by__first_name__icontains'] = self.request.GET.get('meetingOrganizerFirstName', '')
            kwargs['created_by__last_name__icontains'] = self.request.GET.get('meetingOrganizerLastName', '')

        if self.request.GET.get('conferenceRoom', None) is not None:
            try:
                kwargs['conference_room__id'] = int(self.request.GET.get('conferenceRoom'))
            except ValueError:
                pass

        if self.request.GET.get('meetingTitle', None) is not None:
            kwargs['title__icontains'] = self.request.GET.get('meetingTitle', '')

        if self.request.GET.get('meetingRangeDateStart', None) is not None:
            general_functions.fill_date_kwarg(kwargs, 'date__gte', self.request.GET['meetingRangeDateStart'])

        if self.request.GET.get('meetingRangeDateEnd', None) is not None:
            general_functions.fill_date_kwarg(kwargs, 'date__lte', self.request.GET['meetingRangeDateEnd'])


class MeetingDecisionChangeToAcceptedView(PermissionRequiredMixin, View):
    permission_required = 'conference_rooms.moderate_meeting'

    def post(self, request, id):
        meeting = get_object_or_404(Meeting, id=id)

        if not meeting.can_user_moderate(request.user):
            return JsonResponse({'message': 
                _('You are not allowed to accept this meeting.'),}, status=403)

        if meeting.status == Meeting.ACCEPTED_STATUS or meeting.status == Meeting.PENDING_STATUS:
            return JsonResponse({'message': 
                _('The status of this meeting has already been changed.'),}, status=405)

        meeting.status = Meeting.ACCEPTED_STATUS
        meeting.status_changed_by = request.user
        meeting.last_status_change_time = general_functions.current_datetime()
        context = get_meeting_status_change_context(meeting, _('The meeting decision was changed to accepted.'))

        if context['ok']:
            if not meeting.can_user_moderate(meeting.created_by):
                signals.meeting_decision_changed_to_accepted.send(sender=Meeting, instance=meeting)

        return JsonResponse(context, status=200)


class MeetingDecisionChangeToRejectedView(PermissionRequiredMixin, View):
    permission_required = 'conference_rooms.moderate_meeting'

    def post(self, request, id):
        meeting = get_object_or_404(Meeting, id=id)

        if not meeting.can_user_moderate(request.user):
            return JsonResponse({'message': 
                _('You are not allowed to reject this meeting.'),}, status=403)

        if meeting.status == Meeting.REJECTED_STATUS or meeting.status == Meeting.PENDING_STATUS:
            return JsonResponse({'message': 
                _('The status of this meeting has already been changed.'),}, status=405)

        meeting.status = Meeting.REJECTED_STATUS
        meeting.status_changed_by = request.user
        meeting.last_status_change_time = general_functions.current_datetime()
        meeting.rejection_reason = request.POST['reason']
        context = get_meeting_status_change_context(meeting, _('The meeting decision was changed to rejected.'))

        if context['ok']:
            if not meeting.can_user_moderate(meeting.created_by):
                signals.meeting_decision_changed_to_rejected.send(sender=Meeting, instance=meeting)

        return JsonResponse(context, status=200)
