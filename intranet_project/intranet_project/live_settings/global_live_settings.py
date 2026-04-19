import os
import logging
from pathlib import Path

from shutil import copyfile
from multiprocessing import Lock
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import (
        GeneralSettings, CompanySettings, GlpiIntegrationSettings, 
        FilesManagementSettings, AbsenceCalendarSettings, NotifierSettings,
        ConferenceRoomsSettings, LoggingSettings,
    )


logger = logging.getLogger(__name__)
mutex = Lock()


class GlobalLiveSettings:

    def __init__(self):
        self.set_default_general_settings()
        self.set_default_company_settings()
        self.set_default_glpi_integration_settings()
        self.set_default_files_management_settings()
        self.set_default_absence_calendar_settings()
        self.set_default_notifier_settings()
        self.set_default_conference_rooms_settings()
        self.set_default_logging_settings()

    def set_default_general_settings(self):
        self.general = GeneralSettings.get_default()
        self.activate_default_logo()

    def set_general_settings(self, general_settings):
        self.general = general_settings
        self.activate_logo()

    def activate_default_logo(self):
        default_logo_path = os.path.join(settings.MEDIA_ROOT,
                                settings.LIVE_SETTINGS_DEFAULT_LOGO_REL_DIR,
                                settings.LIVE_SETTINGS_DEFAULT_LOGO_FILENAME)

        active_logo_path = os.path.join(settings.MEDIA_ROOT,
                            settings.LIVE_SETTINGS_ACTIVE_LOGO_REL_DIR,
                            settings.LIVE_SETTINGS_ACTIVE_LOGO_FILENAME)

        if Path(default_logo_path).is_file():
            copyfile(default_logo_path, active_logo_path)
        else:
            logger.error(_('Default logo (%(default_logo_name)s) is missing.') \
                % {'default_logo_name': settings.LIVE_SETTINGS_DEFAULT_LOGO_FILENAME})

    def activate_logo(self):
        uploaded_active_path = self.general.logo.path
        active_logo_path = os.path.join(settings.MEDIA_ROOT, 
                            settings.LIVE_SETTINGS_ACTIVE_LOGO_REL_DIR,
                            settings.LIVE_SETTINGS_ACTIVE_LOGO_FILENAME)

        if Path(uploaded_active_path).is_file():
            copyfile(uploaded_active_path, active_logo_path)
        else:
            logger.error(_('Uploaded active logo (%(logo_name)s) is missing.') \
                % {'logo_name': os.path.basename(self.general.logo.name)})

    def set_default_company_settings(self):
        self.company = CompanySettings.get_default()

    def set_company_settings(self, company_settings):
        self.company = company_settings

    def set_default_glpi_integration_settings(self):
        self.glpi_integration = GlpiIntegrationSettings.get_default()

    def set_glpi_integration_settings(self, glpi_integration_settings):
        self.glpi_integration = glpi_integration_settings

    def set_default_files_management_settings(self):
        self.files_management = FilesManagementSettings.get_default()

    def set_files_management_settings(self, files_management_settings):
        self.files_management = files_management_settings

    def set_default_absence_calendar_settings(self):
        self.absence_calendar = AbsenceCalendarSettings.get_default()

    def set_absence_calendar_settings(self, absence_calendar_settings):
        self.absence_calendar = absence_calendar_settings
    
    def set_default_notifier_settings(self):
        self.notifier = NotifierSettings.get_default()

    def set_notifier_settings(self, notifier_settings):
        self.notifier = notifier_settings

    def set_default_conference_rooms_settings(self):
        self.conference_rooms = ConferenceRoomsSettings.get_default()

    def set_conference_rooms_settings(self, conference_rooms_settings):
        self.conference_rooms = conference_rooms_settings

    def set_default_logging_settings(self):
        self.logging = LoggingSettings.get_default()

    def set_logging_settings(self, logging_settings):
        self.logging = logging_settings

    def initialize_global_live_settings(self):
        general_settings = GeneralSettings.get_active()
        if general_settings:
            self.set_general_settings(general_settings)
        
        company_settings = CompanySettings.get_active()
        if company_settings:
            self.set_company_settings(company_settings)
        
        glpi_integration_settings = GlpiIntegrationSettings.get_active()
        if glpi_integration_settings:
            self.set_glpi_integration_settings(glpi_integration_settings)
        
        files_management_settings = FilesManagementSettings.get_active()
        if files_management_settings:
            self.set_files_management_settings(files_management_settings)

        absence_calendar_settings = AbsenceCalendarSettings.get_active()
        if absence_calendar_settings:
            self.set_absence_calendar_settings(absence_calendar_settings)

        notifier_settings = NotifierSettings.get_active()
        if notifier_settings:
            self.set_notifier_settings(notifier_settings)

        conference_rooms_settings = ConferenceRoomsSettings.get_active()
        if conference_rooms_settings:
            self.set_conference_rooms_settings(conference_rooms_settings)

        logging_settings = LoggingSettings.get_active()
        if logging_settings:
            self.set_logging_settings(logging_settings)

    def get_glpi_integration_settings(self):
        with mutex:
            glpi_integration_settings = self.glpi_integration

        return self.glpi_integration


global_live_settings = GlobalLiveSettings()
