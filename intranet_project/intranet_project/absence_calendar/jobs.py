import logging
from datetime import timedelta

from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from live_settings.global_live_settings import global_live_settings
from scheduler import jobs_scheduler
from .models import VacationLeave, SpecialLeave, RemoteWork
from intranet_project import general_functions


logger = logging.getLogger(__name__)


def start():
    start_saving_leaves_documents()


def get_save_leaves_documents_job_id():
    return __name__ + '.save_leaves_documents'


def start_saving_leaves_documents():
    jobs_scheduler.start_job(
        save_leaves_documents,
        get_save_leaves_documents_job_id(),
        global_live_settings.absence_calendar
    )


def reschedule_saving_leaves_documents():
    jobs_scheduler.reschedule_job(
        save_leaves_documents,
        get_save_leaves_documents_job_id(),
        global_live_settings.absence_calendar
    )


def save_leaves_documents():
    general_functions.log_job_info(logger, get_save_leaves_documents_job_id(), 
                            _('Started saving leaves documents.'))
    time_start = timezone.now()

    save_vacation_leaves_documents()
    save_special_leaves_documents()
    save_remote_works_documents()

    time_end = timezone.now()
    general_functions.log_job_info(logger, get_save_leaves_documents_job_id(), 
        _('Finished saving leaves documents in %(work_time)s.') % {'work_time': time_end-time_start})


def save_vacation_leaves_documents():
    vacation_leaves = VacationLeave.objects.filter(
        end_date__lt=general_functions.current_date(),
        status__in=(VacationLeave.ACCEPTED_STATUS, VacationLeave.PENDING_TO_CANCEL_STATUS),
        document=None,
    )

    for vacation_leave in vacation_leaves:
        try:
            vacation_leave.create_document()
        except Exception as e:
            general_functions.log_job_exception(logger, get_save_leaves_documents_job_id(), 
                _('Exception occured while saving vacation leave document(%(vl)s): %(e)s') \
                % {'e': repr(e), 'vl': str(vacation_leave)})


def save_special_leaves_documents():
    special_leaves = SpecialLeave.objects.filter(
        end_date__lt=general_functions.current_date(),
        status__in=(SpecialLeave.CONFIRMED_STATUS, SpecialLeave.PENDING_TO_CANCEL_STATUS),
        document=None,
    ).exclude(confirming_person=None)

    for special_leave in special_leaves:
        try:
            special_leave.create_document()
        except Exception as e:
            general_functions.log_job_exception(logger, get_save_leaves_documents_job_id(), 
                _('Exception occured while saving special leave document(%(sl)s): %(e)s') \
                % {'e': repr(e), 'sl': str(special_leave)})


def save_remote_works_documents():
    remote_works = RemoteWork.objects.filter(
        end_date__lt=general_functions.current_date(),
        status__in=(RemoteWork.ACCEPTED_STATUS, RemoteWork.PENDING_TO_CANCEL_STATUS),
        document=None,
    )

    for remote_work in remote_works:
        try:
            remote_work.create_document()
        except Exception as e:
            general_functions.log_job_exception(logger, get_save_leaves_documents_job_id(), 
                _('Exception occured while saving remote work document(%(rw)s): %(e)s') \
                % {'e': repr(e), 'rw': str(remote_work)})
