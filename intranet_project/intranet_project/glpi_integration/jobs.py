import logging

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apscheduler.triggers.interval import IntervalTrigger

from .glpi_api import GlpiApi
from .updater import CompanyStructureUpdater
from live_settings.global_live_settings import global_live_settings
from scheduler import jobs_scheduler
from intranet_project import general_functions


logger = logging.getLogger(__name__)


def start():
    start_company_structure_sync()


def start_company_structure_sync():
    jobs_scheduler.start_job(
        update_company_structure,
        get_company_structure_sync_job_id(),
        global_live_settings.glpi_integration
    )


def reschedule_company_structure_sync():
    jobs_scheduler.reschedule_job(
        update_company_structure,
        get_company_structure_sync_job_id(),
        global_live_settings.glpi_integration
    )


def get_company_structure_sync_job_id():
    return __name__ + '.company_structure_sync'


def update_company_structure():
    general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
                                _('Starting GLPI synchronization.'))

    time_start = timezone.now()

    glpi_api = download_glpi_data()

    if glpi_api:
        departments_synced = sync_departments(glpi_api)

        if departments_synced:
            sync_users(glpi_api)
    
    time_end = timezone.now()

    general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
        _('GLPI synchronization finished in %(work_time)s.') % {'work_time': time_end-time_start})


def download_glpi_data():
    general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
                            _('Starting GLPI data download.'))

    glpi_integration_settings = global_live_settings.get_glpi_integration_settings()

    try:
        glpi_api = GlpiApi(
            root_url=glpi_integration_settings.url,
            authorization=glpi_integration_settings.authorization,
            app_token=glpi_integration_settings.app_token,
            parent_groups_names_to_sync=glpi_integration_settings.get_parent_groups_names_to_sync(),
            user_account_sync_group_name=glpi_integration_settings.user_account_sync_group,
            user_data_sync_group_name=glpi_integration_settings.user_data_sync_group,
            user_data_sync_from_comment_group_name=glpi_integration_settings.user_data_sync_from_comment_group,
            comment_data_start_separator=glpi_integration_settings.comment_data_start_separator,
            comment_data_end_separator=glpi_integration_settings.comment_data_end_separator,
            region_name_api_key=glpi_integration_settings.region_name_api_key,
            region_code_api_key=glpi_integration_settings.region_code_api_key,
            cities_api_key=glpi_integration_settings.cities_api_key,
            short_cell_phone_number_api_key=glpi_integration_settings.short_cell_phone_number_api_key,
        )
    except Exception as e:
        general_functions.log_job_exception(logger, get_company_structure_sync_job_id(), 
            _('Exception occured while downloading GLPI data: %(e)s')  % {'e': repr(e)})
        return None
    else:
        general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
                        _('GLPI data download finished.'))
        return glpi_api


def sync_departments(glpi_api):
    general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
                _('Starting departments synchronization.'))

    try:
        CompanyStructureUpdater.synchronize_glpi_departments(glpi_api.glpi_groups)
    except Exception as e:
        general_functions.log_job_exception(logger, get_company_structure_sync_job_id(), 
            _('Exception occured while synchronizing departments: %(e)s') % {'e': repr(e)})
        return False
    else:
        general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
            _('Departments synchronization finished.'))
        return True


def sync_users(glpi_api):
    general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
        _('Starting users synchronization.'))

    try:
        CompanyStructureUpdater.synchronize_glpi_users(glpi_api.glpi_users)
    except Exception as e:
        general_functions.log_job_exception(logger, get_company_structure_sync_job_id(), 
            _('Exception occured while synchronizing users: %(e)s') % {'e': repr(e)})
        return False
    else:
        general_functions.log_job_info(logger, get_company_structure_sync_job_id(), 
            _('Users synchronization finished.'))
        return True
