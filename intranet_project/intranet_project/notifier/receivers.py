from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils.translation import gettext_lazy as _
from .consumers import NotificationsConsumer

from .models import Notification
from conference_rooms.models import Meeting
from conference_rooms import signals as conference_rooms_signals
from absence_calendar.models import VacationLeave, SpecialLeave, RemoteWork
from absence_calendar import signals as absence_calendar_signals
from live_settings.global_live_settings import global_live_settings
from notifier.email_thread import send_html_mail
from intranet_project import general_functions
from users.models import Profile
from live_settings import signals as live_settings_signals
from live_settings.models import NotifierSettings
from . import jobs


@receiver(post_save, sender=Notification)
def push_notification_to_frontend(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            NotificationsConsumer.get_group_name(instance.receiver),
            NotificationsConsumer.get_push_notification_dict(instance)
        )


def create_notification(receiver, title, description, redirect_url):
    Notification.objects.create(receiver=receiver, title=title, description=description,
                                redirect_url=redirect_url)


def receiver_accepts_app_notifications(receiver):
    if not receiver.is_active:
        return False

    has_profile = general_functions.get_related_object_or_none(receiver, Profile, 'profile')
    
    if has_profile:
        return receiver.profile.app_notifications

    return False


def receiver_accepts_email_notifications(receiver):
    if not receiver.is_active:
        return False

    has_profile = general_functions.get_related_object_or_none(receiver, Profile, 'profile')
    
    if has_profile:
        return receiver.profile.email_notifications

    return False


@receiver(conference_rooms_signals.meeting_pending, sender=Meeting)
def on_meeting_pending(sender, instance, **kwargs):
    receivers_group = instance.conference_room.location.moderator_group

    if receivers_group:
        receivers = User.objects.filter(groups__id=receivers_group.id)
        redirect_url = reverse('conference_rooms:meetings_moderation')

        for receiver in receivers:
            notify_about_meeting(redirect_url, receiver, instance, _('Meeting pending'), 
                _('The meeting is waiting for your approval.'))


@receiver(conference_rooms_signals.meeting_accepted, sender=Meeting)
def on_meeting_accepted(sender, instance, **kwargs):
    redirect_url = reverse('conference_rooms:user_meetings_accepted')

    notify_about_meeting(redirect_url, instance.created_by, instance, _('Meeting accepted'), 
        _('Your meeting has been accepted.'))


@receiver(conference_rooms_signals.meeting_rejected, sender=Meeting)
def on_meeting_rejected(sender, instance, **kwargs):
    redirect_url = reverse('conference_rooms:user_meetings_rejected')

    notify_about_meeting(redirect_url, instance.created_by, instance, _('Meeting rejected'),
        _('Your meeting has been rejected.'))


@receiver(conference_rooms_signals.meeting_decision_changed_to_accepted, sender=Meeting)
def on_meeting_decision_changed_to_accepted(sender, instance, **kwargs):
    redirect_url = reverse('conference_rooms:user_meetings_accepted')

    notify_about_meeting(redirect_url, instance.created_by, instance, _('Meeting accepted'), 
        _('The decision regarding one of your meetings was changed to accepted.'))


@receiver(conference_rooms_signals.meeting_decision_changed_to_rejected, sender=Meeting)
def on_meeting_decision_changed_to_rejected(sender, instance, **kwargs):
    redirect_url = reverse('conference_rooms:user_meetings_rejected')

    notify_about_meeting(redirect_url, instance.created_by, instance, _('Meeting rejected'),
        _('The decision regarding one of your meetings was changed to rejected.'))


@receiver(conference_rooms_signals.accepted_meeting_updated, sender=Meeting)
def on_accepted_meeting_updated(sender, instance, **kwargs):
    receivers_group = instance.conference_room.location.moderator_group

    if receivers_group:
        receivers = User.objects.filter(groups__id=receivers_group.id)
        redirect_url = reverse('conference_rooms:meetings_moderation')

        for receiver in receivers:
            notify_about_meeting(redirect_url, receiver, instance, _('Meeting modified'), 
                _('The meeting was modified and waits for your reapproval.'))


@receiver(conference_rooms_signals.accepted_meeting_deleted, sender=Meeting)
def on_accepted_meeting_deleted(sender, instance, **kwargs):
    receivers_group = instance.conference_room.location.moderator_group
    
    if receivers_group:
        receivers = User.objects.filter(groups__id=receivers_group.id)
        redirect_url = reverse('conference_rooms:meetings_moderation')

        for receiver in receivers:
            notify_about_meeting(redirect_url, receiver, instance, _('Meeting deleted'),
                _('Accepted meeting has been deleted.'))


def notify_about_meeting(redirect_url, receiver, meeting, title, description):
    description += ('</br></br>' + str(_('Details')) + ':</br><ul>'
                '<li>' + str(_('Conference room')) + f': {meeting.conference_room.name}</li>'
                '<li>' + str(_('Created by')) + f': {meeting.created_by.profile.get_name()}</li>'
                '<li>' + str(_('Time')) + f': {meeting.date} {meeting.start_time.strftime("%H:%M")}' + \
                    f'-{meeting.end_time.strftime("%H:%M")}</li>'
                '</ul>')

    if receiver_accepts_app_notifications(receiver):
        create_notification(receiver, title, description, redirect_url)

    if receiver_accepts_email_notifications(receiver):
        if receiver.email:
            send_html_mail(title, description, [receiver.email,])


@receiver(absence_calendar_signals.vacation_leave_pending, sender=VacationLeave)
def on_vacation_leave_pending(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:vacation_leaves_moderation')

    notify_about_vacation_leave(redirect_url, instance.decisive_person, instance, _('Vacation leave pending'), 
                                    _('A vacation leave is waiting for your approval.'))


@receiver(absence_calendar_signals.vacation_leave_deleted, sender=VacationLeave)
def on_vacation_leave_deleted(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:vacation_leaves_moderation')

    notify_about_vacation_leave(redirect_url, instance.decisive_person, instance, _('Vacation leave deleted'),
                                    _('Vacation leave that was waiting for your approval has been deleted.'))


@receiver(absence_calendar_signals.vacation_leave_accepted, sender=VacationLeave)
def on_vacation_leave_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance, _('Vacation leave accepted'), 
                                    _('Your vacation leave has been accepted.'))
    
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('New vacation leave document'), 
                                        _('New vacation leave document has appeared.'))


@receiver(absence_calendar_signals.vacation_leave_rejected, sender=VacationLeave)
def on_vacation_leave_rejected(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url, instance.absent, instance, _('Vacation leave rejected'), 
                                    _('Your vacation leave has been rejected.'))


@receiver(absence_calendar_signals.vacation_leave_pending_to_finish_earlier, sender=VacationLeave)
def on_vacation_leave_pending_to_finish_earlier(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:vacation_leaves_moderation')
    notify_about_vacation_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Vacation leave pending to finish earlier'),
                                _('Vacation leave accepted by you is pending to finish earlier.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave pending to finish earlier'), 
                                        _('One of vacation leaves is pending to finish earlier.'))


@receiver(absence_calendar_signals.vacation_leave_finished_earlier, sender=VacationLeave)
def on_vacation_leave_finished_earlier(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Request to finish vacation leave earlier accepted'),
                                _('Request to finish vacation leave earlier has been accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave finished earlier'), 
                                        _('One of requests to finish vacation leave earlier was accepted.'))


@receiver(absence_calendar_signals.vacation_leave_request_to_finish_earlier_rejected, sender=VacationLeave)
def on_vacation_leave_request_to_finish_earlier_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Request to finish vacation leave earlier rejected'),
                                _('Request to finish vacation leave earlier has been rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Request to finish vacation leave earlier rejected'), 
                                        _('Request to finish vacation leave earlier has been rejected.'))


@receiver(absence_calendar_signals.accepted_vacation_leave_updated, sender=VacationLeave)
def on_accepted_vacation_leave_updated(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:vacation_leaves_moderation')
    notify_about_vacation_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Vacation leave updated'),
                                _('Vacation leave accepted by you was updated and waits for your reapproval.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave updated'), 
                                        _('Vacation leave has been updated and now waits for reapproval' + \
                                        ' from decisive person.'))


@receiver(absence_calendar_signals.vacation_leave_decisive_changed, sender=VacationLeave)
def on_vacation_leave_decisive_changed(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:vacation_leaves_moderation')
    notify_about_vacation_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Vacation leave decisive person changed'),
                                _('The decisive person in the vacation leave you were responsible for has changed. ' + \
                                'You are no longer responsible for this vacation leave.'))


@receiver(absence_calendar_signals.vacation_leave_canceled, sender=VacationLeave)
def on_vacation_leave_canceled(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Vacation leave canceled'),
                                _('Cancelation of your vacation leave was accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave canceled'), 
                                        _('One of vacation leaves has been canceled.'))


@receiver(absence_calendar_signals.vacation_leave_cancelation_rejected, sender=VacationLeave)
def on_vacation_leave_cancelation_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Vacation leave cancelation rejected'),
                                _('Cancelation of your vacation leave was rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave cancelation rejected'), 
                                        _('One of vacation leaves cancelation has been rejected.'))


@receiver(absence_calendar_signals.vacation_leave_decision_changed_accepted, sender=VacationLeave)
def on_vacation_leave_decision_changed_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Vacation leave decision changed'),
                                _('The decision regarding your vacation leave was changed to accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('New vacation leave document'), 
                                        _('New vacation leave document has appeared.'))


@receiver(absence_calendar_signals.vacation_leave_decision_changed_rejected, sender=VacationLeave)
def on_vacation_leave_decision_changed_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_vacation_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Vacation leave decision changed'),
                                _('The decision regarding your vacation leave was changed to rejected.'))
                                
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave decision changed'), 
                                        _('Vacation leave that previously was accepted, has ' + \
                                            'been rejected by decisive.'))


@receiver(absence_calendar_signals.vacation_leave_pending_to_cancel, sender=VacationLeave)
def on_vacation_leave_pending_to_cancel(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:vacation_leaves_moderation')
    notify_about_vacation_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Vacation leave is pending to cancel'),
                                _('One of vacation leaves you accepted is pending to cancel.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:vacation_leaves_applications')

        for receiver in receivers:
            notify_about_vacation_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Vacation leave pending to cancel'), 
                                        _('One of vacation leaves is pending to cancel.'))


def notify_about_vacation_leave(redirect_url, receiver, vacation_leave, title, description):
    description += ('</br></br>' + str(_('Details')) + ':</br><ul>'
                '<li>' + str(_('Absent')) + f': {vacation_leave.absent.profile.get_name()}</li>'
                '<li>' + str(_('From')) + f': {vacation_leave.start_date}</li>'
                '<li>' + str(_('To')) + f': {vacation_leave.end_date}</li>'
                '</ul>')

    if receiver_accepts_app_notifications(receiver):
        create_notification(receiver, title, description, redirect_url)

    if receiver_accepts_email_notifications(receiver):
        if receiver.email:
            send_html_mail(title, description, [receiver.email,])


@receiver(absence_calendar_signals.special_leave_pending, sender=SpecialLeave)
def on_special_leave_pending(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:special_leaves_moderation')

    notify_about_special_leave(redirect_url, instance.decisive_person, instance, _('Special leave pending'), 
                                    _('A special leave is waiting for your approval.'))


@receiver(absence_calendar_signals.special_leave_deleted, sender=SpecialLeave)
def on_special_leave_deleted(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:special_leaves_moderation')

    notify_about_special_leave(redirect_url, instance.decisive_person, instance, _('Special leave deleted'),
                                    _('Special leave that was waiting for your approval has been deleted.'))


@receiver(absence_calendar_signals.special_leave_accepted, sender=SpecialLeave)
def on_special_leave_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Special leave accepted'), 
                                _('Your special leave has been accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance, _('New special leave'), 
                                        _('New special leave has appeared.'))


@receiver(absence_calendar_signals.special_leave_rejected, sender=SpecialLeave)
def on_special_leave_rejected(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url, instance.absent, instance, _('Special leave rejected'), 
                                    _('Your special leave has been rejected.'))


@receiver(absence_calendar_signals.special_leave_finished_earlier, sender=SpecialLeave)
def on_special_leave_finished_earlier(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Request for special leave to finish earlier accepted'),
                                _('Request for special leave to finish earlier has been accepted'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Request for special leave to finish earlier accepted'), 
                                        _('One of special leave requests to finish earlier has been accepted.'))


@receiver(absence_calendar_signals.special_leave_pending_to_finish_earlier, sender=SpecialLeave)
def on_special_leave_pending_to_finish_earlier(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:special_leaves_moderation')
    notify_about_special_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Special leave pending to finish earlier'),
                                _('One of special leaves that you accepted is pending to finish earlier.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave pending to finish earlier'), 
                                        _('One of special leaves is pending to finish earlier.'))


@receiver(absence_calendar_signals.special_leave_request_to_finish_earlier_rejected, sender=SpecialLeave)
def on_special_leave_request_to_finish_earlier_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Request for special leave to finish earlier rejected'),
                                _('Request for special leave to finish earlier has been rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Request for special leave to finish earlier rejected'), 
                                        _('One of special leave requests to finish earlier has been rejected.'))


@receiver(absence_calendar_signals.accepted_special_leave_updated, sender=SpecialLeave)
def on_accepted_special_leave_updated(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:special_leaves_moderation')
    notify_about_special_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Special leave updated'),
                                _('One of special leaves you accepted has been updated and ' + \
                                    'waits for your reapproval.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave updated'), 
                                        _('One of special leaves was updated and now needs to be reapproved.'))


@receiver(absence_calendar_signals.special_leave_decisive_changed, sender=SpecialLeave)
def on_special_leave_decisive_changed(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:special_leaves_moderation')
    notify_about_special_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Special leave decisive person changed'),
                                _('The decisive person in the special leave you were responsible for has changed. ' + \
                                'You are no longer responsible for this vacation leave.'))


@receiver(absence_calendar_signals.special_leave_pending_to_cancel, sender=SpecialLeave)
def on_special_leave_pending_to_cancel(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:special_leaves_moderation')
    notify_about_special_leave(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Special leave is pending to cancel'),
                                _('One of special leaves you accepted is pending to cancel.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave is pending to cancel'), 
                                        _('One of special leaves is pending to cancel.'))


@receiver(absence_calendar_signals.special_leave_canceled, sender=SpecialLeave)
def on_special_leave_canceled(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_vacation_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Special leave canceled'),
                                _('Cancelation of your special leave was accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave canceled'), 
                                        _('One of special leaves has been canceled.'))


@receiver(absence_calendar_signals.special_leave_cancelation_rejected, sender=SpecialLeave)
def on_special_leave_cancelation_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Special leave cancelation rejected'),
                                _('Cancelation of your special leave was rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave cancelation rejected'), 
                                        _('One of special leaves cancelation has been rejected.'))


@receiver(absence_calendar_signals.special_leave_decision_changed_accepted, sender=SpecialLeave)
def on_special_leave_decision_changed_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance,
                                _('Special leave decision changed'),
                                _('The decision regarding your special leave was changed to accepted.'))
    
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('New special leave'), 
                                        _('New special leave has appeared.'))


@receiver(absence_calendar_signals.special_leave_decision_changed_rejected, sender=SpecialLeave)
def on_special_leave_decision_changed_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance, 
                                _('Special leave decision changed'),
                                _('The decision regarding your special leave was changed to rejected.'))
    
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave decision changed'), 
                                        _('The decision regarding one of special leaves has ' + \
                                            'been changed to rejected.'))


@receiver(absence_calendar_signals.special_leave_confirmation_document_confirmed, sender=SpecialLeave)
def on_special_leave_confirmation_document_confirmed(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_special_leaves')
    notify_about_special_leave(redirect_url_for_absent, instance.absent, instance, _('Special leave confirmed'), 
                                    _('Your special leave has been confirmed.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:special_leaves_applications')

        for receiver in receivers:
            notify_about_special_leave(redirect_url_for_payroll_department, receiver, instance,
                                        _('Special leave confirmed'), 
                                        _('One of special leaves has been confirmed.'))


def notify_about_special_leave(redirect_url, receiver, special_leave, title, description):
    description += ('</br></br>' + str(_('Details')) + ':</br><ul>'
                '<li>' + str(_('Absent')) + f': {special_leave.absent.profile.get_name()}</li>'
                '<li>' + str(_('From')) + f': {special_leave.start_date}</li>'
                '<li>' + str(_('To')) + f': {special_leave.end_date}</li>'
                '</ul>')

    if receiver_accepts_app_notifications(receiver):
        create_notification(receiver, title, description, redirect_url)

    if receiver_accepts_email_notifications(receiver):
        if receiver.email:
            send_html_mail(title, description, [receiver.email,])

### RemoteWork ###

@receiver(absence_calendar_signals.remote_work_pending, sender=RemoteWork)
def on_remote_work_pending(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:remote_work_moderation')

    notify_about_remote_work(redirect_url, instance.decisive_person, instance, _('Remote work pending'), 
                                    _('A remote work is waiting for your approval.'))


@receiver(absence_calendar_signals.remote_work_deleted, sender=RemoteWork)
def on_remote_work_deleted(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:remote_work_moderation')

    notify_about_remote_work(redirect_url, instance.decisive_person, instance, _('Remote work deleted'),
                                    _('Remote work that was waiting for your approval has been deleted.'))


@receiver(absence_calendar_signals.remote_work_accepted, sender=RemoteWork)
def on_remote_work_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance, _('Remote work accepted'), 
                                    _('Your remote work has been accepted.'))
    
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('New remote work document'), 
                                        _('New remote work document has appeared.'))


@receiver(absence_calendar_signals.remote_work_rejected, sender=RemoteWork)
def on_remote_work_rejected(sender, instance, **kwargs):
    redirect_url = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url, instance.absent, instance, _('Remote work rejected'), 
                                    _('Your remote work has been rejected.'))


@receiver(absence_calendar_signals.remote_work_pending_to_finish_earlier, sender=RemoteWork)
def on_remote_work_pending_to_finish_earlier(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:remote_work_moderation')
    notify_about_remote_work(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Remote work pending to finish earlier'),
                                _('Remote work accepted by you is pending to finish earlier.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work pending to finish earlier'), 
                                        _('One of remote works is pending to finish earlier.'))


@receiver(absence_calendar_signals.remote_work_finished_earlier, sender=RemoteWork)
def on_remote_work_finished_earlier(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Request to finish remote work earlier accepted'),
                                _('Request to finish remote work earlier has been accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work finished earlier'), 
                                        _('One of requests to finish remote work earlier was accepted.'))


@receiver(absence_calendar_signals.remote_work_request_to_finish_earlier_rejected, sender=RemoteWork)
def on_remote_work_request_to_finish_earlier_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Request to finish remote work earlier rejected'),
                                _('Request to finish remote work earlier has been rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Request to finish remote work earlier rejected'), 
                                        _('Request to finish remote work earlier has been rejected.'))


@receiver(absence_calendar_signals.accepted_remote_work_updated, sender=RemoteWork)
def on_accepted_remote_work_updated(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:remote_work_moderation')
    notify_about_remote_work(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Remote work updated'),
                                _('Remote work accepted by you was updated and waits for your reapproval.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work updated'), 
                                        _('Remote work has been updated and now waits for reapproval' + \
                                        ' from decisive person.'))


@receiver(absence_calendar_signals.remote_work_decisive_changed, sender=RemoteWork)
def on_remote_work_decisive_changed(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:remote_work_moderation')
    notify_about_remote_work(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Remote work decisive person changed'),
                                _('The decisive person in the remote work you were responsible for has changed. ' + \
                                'You are no longer responsible for this remote work.'))


@receiver(absence_calendar_signals.remote_work_canceled, sender=RemoteWork)
def on_remote_work_canceled(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Remote work canceled'),
                                _('Cancelation of your remote work was accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work canceled'), 
                                        _('One of remote works has been canceled.'))


@receiver(absence_calendar_signals.remote_work_cancelation_rejected, sender=RemoteWork)
def on_remote_work_cancelation_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Remote work cancelation rejected'),
                                _('Cancelation of your remote work was rejected.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work cancelation rejected'), 
                                        _('One of remote works cancelation has been rejected.'))


@receiver(absence_calendar_signals.remote_work_decision_changed_accepted, sender=RemoteWork)
def on_remote_work_decision_changed_accepted(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Remote work decision changed'),
                                _('The decision regarding your remote work was changed to accepted.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('New remote work document'), 
                                        _('New remote work document has appeared.'))


@receiver(absence_calendar_signals.remote_work_decision_changed_rejected, sender=RemoteWork)
def on_remote_work_decision_changed_rejected(sender, instance, **kwargs):
    redirect_url_for_absent = reverse('absence_calendar:user_remote_works')
    notify_about_remote_work(redirect_url_for_absent, instance.absent, instance,
                                _('Remote work decision changed'),
                                _('The decision regarding your remote work was changed to rejected.'))
                                
    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work decision changed'), 
                                        _('Remote work that previously was accepted, has ' + \
                                            'been rejected by decisive.'))


@receiver(absence_calendar_signals.remote_work_pending_to_cancel, sender=RemoteWork)
def on_remote_work_pending_to_cancel(sender, instance, **kwargs):
    redirect_url_for_decisive = reverse('absence_calendar:remote_work_moderation')
    notify_about_remote_work(redirect_url_for_decisive, instance.decisive_person, instance,
                                _('Remote work is pending to cancel'),
                                _('One of remote works you accepted is pending to cancel.'))

    if global_live_settings.absence_calendar.payroll_department_group is not None:
        receivers = User.objects.filter(groups__id=
                    global_live_settings.absence_calendar.payroll_department_group.id)
        redirect_url_for_payroll_department = reverse('absence_calendar:remote_works_applications')

        for receiver in receivers:
            notify_about_remote_work(redirect_url_for_payroll_department, receiver, instance,
                                        _('Remote work pending to cancel'), 
                                        _('One of remote works is pending to cancel.'))


def notify_about_remote_work(redirect_url, receiver, remote_work, title, description):
    description += ('</br></br>' + str(_('Details')) + ':</br><ul>'
                '<li>' + str(_('Absent')) + f': {remote_work.absent.profile.get_name()}</li>'
                '<li>' + str(_('From')) + f': {remote_work.start_date}</li>'
                '<li>' + str(_('To')) + f': {remote_work.end_date}</li>'
                '</ul>')

    if receiver_accepts_app_notifications(receiver):
        create_notification(receiver, title, description, redirect_url)

    if receiver_accepts_email_notifications(receiver):
        if receiver.email:
            send_html_mail(title, description, [receiver.email,])

### NOTIFICATIONS REMOVAL JOB SIGNALS ###

@receiver(live_settings_signals.notifier_schedule_changed, sender=NotifierSettings)
def on_notifier_settings_changed(sender, instance, **kwargs):
    jobs.reschedule_removing_notifications()

### NOTIFICATIONS REMOVAL JOB SIGNALS END ###
