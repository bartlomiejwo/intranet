import logging
from datetime import timedelta

from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import IntranetFile
from live_settings.global_live_settings import global_live_settings
from scheduler import jobs_scheduler
from intranet_project import general_functions


logger = logging.getLogger(__name__)


def start():
    start_removing_unused_files()


def get_remove_unused_files_job_id():
    return __name__ + '.remove_unused_files'


def start_removing_unused_files():
    jobs_scheduler.start_job(
        remove_unused_files,
        get_remove_unused_files_job_id(),
        global_live_settings.files_management
    )


def reschedule_removing_unused_files():
    jobs_scheduler.reschedule_job(
        remove_unused_files,
        get_remove_unused_files_job_id(),
        global_live_settings.files_management
    )


def remove_unused_files():
    general_functions.log_job_info(logger, get_remove_unused_files_job_id(), 
                        _('Starting removal of unused uploaded files.'))
    time_start = timezone.now()

    one_day_before_now = timezone.now() - timedelta(days=1)

    files_to_delete = IntranetFile.objects.filter(
        added_with_wysiwyg=True,
        usage_counter__lte=0,
        upload_date__lte=one_day_before_now,
    )

    number_of_files_to_delete = len(files_to_delete)
    files_to_delete.delete()
    general_functions.log_job_info(logger, get_remove_unused_files_job_id(), 
        _('%(number)s files were removed.') % {'number': number_of_files_to_delete})

    time_end = timezone.now()
    general_functions.log_job_info(logger, get_remove_unused_files_job_id(), 
        _('Removal of unused uploaded files finished in %(work_time)s.') % {'work_time': time_end-time_start})
