from datetime import datetime
import os

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import User, Group

from intranet_project import general_functions


class GeneralSettings(models.Model):
    class Meta:
        verbose_name = _('general settings')
        verbose_name_plural = _('general settings')

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    active = models.BooleanField(default=False, verbose_name=_('active'))

    website_name = models.CharField(max_length=100, verbose_name=_('website name'))
    admin_website_name = models.CharField(max_length=100, verbose_name=_('admin website name'))
    logo = models.ImageField(
        default=settings.LIVE_SETTINGS_DEFAULT_LOGO_FILENAME,
        upload_to=settings.LIVE_SETTINGS_UPLOAD_REL_DIR,
        help_text=_('Image should be in PNG format.'),
        verbose_name=_('logo')
    )

    def clean(self):
        self.validate_active()
        self.validate_logo_format()

    def validate_active(self):
        if self.active:
            active_general_settings = GeneralSettings.get_active()

            if active_general_settings and self != active_general_settings:
                raise ValidationError(
                    _('There can be only one active general settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_general_settings_exceeded',
                    params={'current_active': active_general_settings}
                )
    
    def validate_logo_format(self):
        ext = general_functions.get_file_extension(self.logo.path)

        if not ext:
            raise ValidationError(
                _('Wrong image format. Image format should be PNG.'),
                code='wrong_image_format',
            )

        if ext != '.png' and ext != '.PNG':
            raise ValidationError(
                _('Wrong image format. Image format should be PNG.'),
                code='wrong_image_format',
            )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(GeneralSettings, active=True)

    @staticmethod
    def get_default():
        return GeneralSettings(
            name = 'Default',
            website_name = _('Default website name'),
            admin_website_name = _('Default administration website name'),
            logo = os.path.join(
                settings.LIVE_SETTINGS_ACTIVE_LOGO_REL_DIR,
                settings.LIVE_SETTINGS_ACTIVE_LOGO_FILENAME
            )
        )


class CompanySettings(models.Model):
    class Meta:
        verbose_name = _('company settings')
        verbose_name_plural = _('company settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    city = models.CharField(max_length=50, unique=True, verbose_name=_('city'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_company_settings = CompanySettings.get_active()

            if active_company_settings and self != active_company_settings:
                raise ValidationError(
                    _('There can be only one active company settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_company_settings_exceeded',
                    params={'current_active': active_company_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(CompanySettings, active=True)

    @staticmethod
    def get_default():
        return CompanySettings(
            name = force_text(_('Default company name')),
            city = force_text(_('Default city')),
        )


class GlpiIntegrationSettings(models.Model):
    class Meta:
        verbose_name = _('GLPI integration settings')
        verbose_name_plural = _('GLPI integration settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    
    url = models.CharField(max_length=300, verbose_name=_('url'))
    authorization = models.CharField(max_length=100, verbose_name=_('authorization'))
    app_token = models.CharField(max_length=100, verbose_name=_('app token'))

    parent_groups_names_to_sync = models.CharField(max_length=500, verbose_name=_('parent groups names to sync'))
    user_account_sync_group = models.CharField(max_length=100, verbose_name=_('user account sync group'))
    user_data_sync_group = models.CharField(max_length=100, verbose_name=_('user_data_sync_group'))
    user_data_sync_from_comment_group = models.CharField(max_length=100,
                                            verbose_name=_('user_data_sync_from_comment_group'))

    comment_data_start_separator = models.CharField(max_length=30, verbose_name=_('comment data start separator'))
    comment_data_end_separator = models.CharField(max_length=30, verbose_name=_('comment data end separator'))

    region_name_api_key = models.CharField(max_length=30, verbose_name=_('region name api key'))
    region_code_api_key = models.CharField(max_length=30, verbose_name=_('region code api key'))
    cities_api_key = models.CharField(max_length=30, verbose_name=_('cities api key'))
    short_cell_phone_number_api_key = models.CharField(max_length=30,
                                                        verbose_name=_('short cell phone number api key'))

    enabled = models.BooleanField(default=False, verbose_name=_('enabled'))
    weeks = models.IntegerField(default=0, verbose_name=_('weeks'))
    days = models.IntegerField(default=0, verbose_name=_('days'))
    hours = models.IntegerField(default=1, verbose_name=_('hours'))
    minutes = models.IntegerField(default=0, verbose_name=_('minutes'))
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name=_('next run time'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_glpi_integration_settings = GlpiIntegrationSettings.get_active()

            if active_glpi_integration_settings and self != active_glpi_integration_settings:
                raise ValidationError(
                    _('There can be only one active glpi_integration settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_glpi_integration_settings_exceeded',
                    params={'current_active': active_glpi_integration_settings}
                )

    def __str__(self):
        return self.name

    def get_parent_groups_names_to_sync(self):
        parent_groups_names_to_sync = self.parent_groups_names_to_sync

        if parent_groups_names_to_sync[-1] == ',':
            parent_groups_names_to_sync = parent_groups_names_to_sync[:-1]

        return parent_groups_names_to_sync.split(',')

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(GlpiIntegrationSettings, active=True)

    @staticmethod
    def get_default():
        return GlpiIntegrationSettings(
            name=force_text(_('Default GLPI')),
            url='',
            authorization='',
            app_token='',
            parent_groups_names_to_sync='',
            user_account_sync_group='',
            user_data_sync_group='',
            user_data_sync_from_comment_group='',
            comment_data_start_separator='',
            comment_data_end_separator='',
            region_name_api_key='',
            region_code_api_key='',
            cities_api_key='',
            short_cell_phone_number_api_key='',
            enabled=False,
            weeks=0,
            days=1,
            hours=0,
            minutes=0,
            next_run_time=None
        )


class FilesManagementSettings(models.Model):
    class Meta:
        verbose_name = _('files management settings')
        verbose_name_plural = _('files management settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))

    max_file_size = models.PositiveIntegerField(help_text=_('Maximum file size in megabytes.'),
                                                verbose_name=_('max file size'))

    enabled = models.BooleanField(default=False, verbose_name=_('enabled'))
    weeks = models.IntegerField(default=0, verbose_name=_('weeks'))
    days = models.IntegerField(default=1, verbose_name=_('days'))
    hours = models.IntegerField(default=0, verbose_name=_('hours'))
    minutes = models.IntegerField(default=0, verbose_name=_('minutes'))
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name=_('next run time'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_files_management_settings = FilesManagementSettings.get_active()

            if active_files_management_settings and self != active_files_management_settings:
                raise ValidationError(
                    _('There can be only one active files management settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_files_management_settings_exceeded',
                    params={'current_active': active_files_management_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(FilesManagementSettings, active=True)

    @staticmethod
    def get_default():
        return FilesManagementSettings(
            max_file_size=10,
            enabled=False,
            weeks=0,
            days=1,
            hours=0,
            minutes=0,
            next_run_time=None
        )


class AbsenceCalendarSettings(models.Model):
    class Meta:
        verbose_name = _('absence calendar settings')
        verbose_name_plural = _('absence calendar settings')
    
    active = models.BooleanField(default=False, verbose_name=_('active'))
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))

    payroll_department_group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL,
                                                verbose_name=_('payroll department group'))
    
    risk_assessment_url = models.URLField(default='#', null=False, blank=False,
                                        verbose_name=_('risk assessment URL'))
    safety_rules_url = models.URLField(default='#', null=False, blank=False, 
                                        verbose_name=_('safety rules URL'))
    personal_data_protection_url = models.URLField(default='#', null=False, blank=False, 
                                        verbose_name=_('personal data protection URL'))

    enabled = models.BooleanField(default=False, verbose_name=_('enabled'))
    weeks = models.IntegerField(default=0, verbose_name=_('weeks'))
    days = models.IntegerField(default=1, verbose_name=_('days'))
    hours = models.IntegerField(default=0, verbose_name=_('hours'))
    minutes = models.IntegerField(default=0, verbose_name=_('minutes'))
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name=_('next run time'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_absence_calendar_settings = AbsenceCalendarSettings.get_active()

            if active_absence_calendar_settings and self != active_absence_calendar_settings:
                raise ValidationError(
                    _('There can be only one active company settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_absence_calendar_settings_exceeded',
                    params={'current_active': active_absence_calendar_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(AbsenceCalendarSettings, active=True)

    @staticmethod
    def get_default():
        return AbsenceCalendarSettings(
            name = force_text(_('Default absence calendar settings name')),
            payroll_department_group = None,
            risk_assessment_url='#',
            safety_rules_url='#',
            personal_data_protection_url='#',
            enabled=False,
            weeks=0,
            days=1,
            hours=0,
            minutes=0,
            next_run_time=None
        )


class NotifierSettings(models.Model):
    class Meta:
        verbose_name = _('notifier settings')
        verbose_name_plural = _('notifier settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    email_subject_prefix = models.CharField(max_length=150, blank=True, verbose_name=_('email subject prefix'))
    email_subject_suffix = models.CharField(max_length=150, blank=True, verbose_name=_('email subject suffix'))
    email_footer = models.TextField(blank=True, verbose_name=_('email footer'))

    enabled = models.BooleanField(default=False, verbose_name=_('enabled'))
    remove_only_checked = models.BooleanField(default=True, verbose_name=_('remove only checked'))
    remove_older_than = models.IntegerField(default=12, verbose_name=_('remove older than'), help_text=_('Weeks'))
    weeks = models.IntegerField(default=0, verbose_name=_('weeks'))
    days = models.IntegerField(default=1, verbose_name=_('days'))
    hours = models.IntegerField(default=0, verbose_name=_('hours'))
    minutes = models.IntegerField(default=0, verbose_name=_('minutes'))
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name=_('next run time'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_notifier_settings = NotifierSettings.get_active()

            if active_notifier_settings and self != active_notifier_settings:
                raise ValidationError(
                    _('There can be only one active notifier settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_notifier_settings_exceeded',
                    params={'current_active': active_notifier_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(NotifierSettings, active=True)

    @staticmethod
    def get_default():
        return NotifierSettings(
            name= force_text(_('Default notifier settings')),
            email_subject_prefix='',
            email_subject_suffix='',
            email_footer='',
            enabled=False,
            remove_only_checked=True,
            remove_older_than=12,
            weeks=4,
            days=0,
            hours=0,
            minutes=0,
            next_run_time=None
        )


class ConferenceRoomsSettings(models.Model):
    class Meta:
        verbose_name = _('conference rooms settings')
        verbose_name_plural = _('conference rooms settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    start_hour = models.PositiveIntegerField(verbose_name=_('start hour'))
    end_hour = models.PositiveIntegerField(verbose_name=_('end hour'))
    desired_rooms_number = models.PositiveIntegerField(verbose_name=_('desired rooms number'))


    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_conference_rooms_settings = ConferenceRoomsSettings.get_active()

            if active_conference_rooms_settings and self != active_conference_rooms_settings:
                raise ValidationError(
                    _('There can be only one active conference rooms settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_conference_rooms_settings_exceeded',
                    params={'current_active': active_conference_rooms_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(ConferenceRoomsSettings, active=True)

    @staticmethod
    def get_default():
        return ConferenceRoomsSettings(
            name=force_text(_('Default conference rooms settings')),
            start_hour=7,
            end_hour=18,
            desired_rooms_number=6,
        )


class UsefulLink(models.Model):
    class Meta:
        verbose_name = _('useful link')
        verbose_name_plural = _('useful links')

    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    url = models.CharField(max_length=255, unique=True, verbose_name=_('url'))
    position = models.PositiveSmallIntegerField(unique=True, verbose_name=_('position'))

    def __str__(self):
        return self.name


class LoggingSettings(models.Model):
    class Meta:
        verbose_name = _('logging settings')
        verbose_name_plural = _('logging settings')

    active = models.BooleanField(default=False, verbose_name=_('active'))
    name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))

    enabled = models.BooleanField(default=False, verbose_name=_('enabled'))
    remove_older_than = models.IntegerField(default=26, verbose_name=_('remove older than'), help_text=_('Weeks'))
    weeks = models.IntegerField(default=0, verbose_name=_('weeks'))
    days = models.IntegerField(default=1, verbose_name=_('days'))
    hours = models.IntegerField(default=0, verbose_name=_('hours'))
    minutes = models.IntegerField(default=0, verbose_name=_('minutes'))
    next_run_time = models.DateTimeField(blank=True, null=True, verbose_name=_('next run time'))

    def clean(self):
        self.validate_active()

    def validate_active(self):
        if self.active:
            active_logging_settings = LoggingSettings.get_active()

            if active_logging_settings and self != active_logging_settings:
                raise ValidationError(
                    _('There can be only one active logging settings \
                        (current active: %(current_active)s).'),
                    code='maximum_number_of_active_logging_settings_exceeded',
                    params={'current_active': active_notifier_settings}
                )

    def __str__(self):
        return self.name

    @staticmethod
    def get_active():
        return general_functions.get_object_or_none(LoggingSettings, active=True)

    @staticmethod
    def get_default():
        return LoggingSettings(
            name= force_text(_('Default logging settings')),
            enabled=False,
            remove_older_than=26,
            weeks=4,
            days=0,
            hours=0,
            minutes=0,
            next_run_time=None
        )


def schedule_differs(settings1, settings2):
    if settings1.enabled != settings2.enabled:
        return True

    if settings1.weeks != settings2.weeks:
        return True

    if settings1.days != settings2.days:
        return True
    
    if settings1.hours != settings2.hours:
        return True
    
    if settings1.minutes != settings2.minutes:
        return True

    if settings1.next_run_time != settings2.next_run_time:
        return True
    
    return False
