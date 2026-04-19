import logging
from datetime import timedelta

from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import JobLog
from live_settings.global_live_settings import global_live_settings
from scheduler import jobs_scheduler
from intranet_project import general_functions


logger = logging.getLogger(__name__)


def start():
    start_removing_logs()


def get_remove_logs_job_id():
    return __name__ + '.remove_logs'


def start_removing_logs():
    jobs_scheduler.start_job(
        remove_logs,
        get_remove_logs_job_id(),
        global_live_settings.logging
    )


def reschedule_removing_logs():
    jobs_scheduler.reschedule_job(
        remove_logs,
        get_remove_logs_job_id(),
        global_live_settings.logging
    )


def remove_logs():
    general_functions.log_job_info(logger, get_remove_logs_job_id(), 
                        _('Starting removal of logs.'))
    time_start = timezone.now()

    weeks_before_now = timezone.now() - timedelta(weeks=global_live_settings.logging.remove_older_than)

    logs_to_delete = JobLog.objects.filter(log_time__lte=weeks_before_now,)
    deleted_logs = len(logs_to_delete)
    logs_to_delete.delete()

    time_end = timezone.now()
    general_functions.log_job_info(logger, get_remove_logs_job_id(), 
        _('Removal of %(deleted_logs)s logs finished in %(work_time)s.') \
            % {'deleted_logs': deleted_logs, 'work_time': time_end-time_start})
