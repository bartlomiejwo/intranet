import logging
from datetime import timedelta

from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Notification
from live_settings.global_live_settings import global_live_settings
from scheduler import jobs_scheduler
from intranet_project import general_functions


logger = logging.getLogger(__name__)


def start():
    start_removing_notifications()


def get_remove_notifications_job_id():
    return __name__ + '.remove_notifications'


def start_removing_notifications():
    jobs_scheduler.start_job(
        remove_notifications,
        get_remove_notifications_job_id(),
        global_live_settings.notifier
    )


def reschedule_removing_notifications():
    jobs_scheduler.reschedule_job(
        remove_notifications,
        get_remove_notifications_job_id(),
        global_live_settings.notifier
    )


def remove_notifications():
    general_functions.log_job_info(logger, get_remove_notifications_job_id(), 
                        _('Starting removal of notifications.'))
    time_start = timezone.now()

    weeks_before_now = timezone.now() - timedelta(weeks=global_live_settings.notifier.remove_older_than)
    checked_states = (True,) if global_live_settings.notifier.remove_only_checked else (True, False)

    notifications_to_delete = Notification.objects.filter(
        checked__in=checked_states,
        date_created__lte=weeks_before_now,
    )
    deleted_notifications = len(notifications_to_delete)
    notifications_to_delete.delete()

    time_end = timezone.now()
    general_functions.log_job_info(logger, get_remove_notifications_job_id(), 
        _('Removal of %(deleted_notifications)s notifications finished in %(work_time)s.') \
            % {'deleted_notifications': deleted_notifications, 'work_time': time_end-time_start})
