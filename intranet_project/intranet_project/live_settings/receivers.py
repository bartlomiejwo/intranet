from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import (
    GeneralSettings, CompanySettings,
    GlpiIntegrationSettings, FilesManagementSettings,
    AbsenceCalendarSettings, NotifierSettings,
    ConferenceRoomsSettings, LoggingSettings,
    schedule_differs
)
from . import signals
from .global_live_settings import global_live_settings
from intranet_project import general_functions


@receiver(post_save, sender=GeneralSettings)
def on_general_settings_saved(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_general_settings(instance)
    else:
        active_general_settings = GeneralSettings.get_active()

        if not active_general_settings:
            global_live_settings.set_default_general_settings()


@receiver(post_delete, sender=GeneralSettings)
def on_general_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_default_general_settings()


@receiver(post_save, sender=CompanySettings)
def on_company_settings_saved(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_company_settings(instance)
    else:
        active_company_settings = CompanySettings.get_active()

        if not active_company_settings:
            global_live_settings.set_default_company_settings()


@receiver(post_delete, sender=CompanySettings)
def on_company_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_default_company_settings()


@receiver(post_save, sender=GlpiIntegrationSettings)
def on_glpi_integration_settings_saved(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.glpi_integration)
            
        global_live_settings.set_glpi_integration_settings(instance)

        if schedule_changed:
            signals.glpi_integration_schedule_changed.send(
                sender=GlpiIntegrationSettings,
                instance=global_live_settings.glpi_integration
            )
    else:
        active_glpi_integration_settings = GlpiIntegrationSettings.get_active()

        if not active_glpi_integration_settings:
            schedule_changed = schedule_differs(instance, global_live_settings.glpi_integration)
            
            global_live_settings.set_default_glpi_integration_settings()

            if schedule_changed:
                signals.glpi_integration_schedule_changed.send(
                    sender=GlpiIntegrationSettings,
                    instance=global_live_settings.glpi_integration
                )


@receiver(post_delete, sender=GlpiIntegrationSettings)
def on_glpi_integration_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.glpi_integration)

        global_live_settings.set_default_glpi_integration_settings()

        if schedule_changed:
            signals.glpi_integration_schedule_changed.send(
                sender=GlpiIntegrationSettings,
                instance=global_live_settings.glpi_integration
            )


@receiver(post_save, sender=FilesManagementSettings)
def on_files_management_settings_saved(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.files_management)
        global_live_settings.set_files_management_settings(instance)

        if schedule_changed:
            signals.files_management_schedule_changed.send(
                sender=FilesManagementSettings,
                instance=global_live_settings.files_management
            )
    else:
        active_files_management_settings = FilesManagementSettings.get_active()

        if not active_files_management_settings:
            schedule_changed = schedule_differs(instance, global_live_settings.files_management)
            global_live_settings.set_default_files_management_settings()

            if schedule_changed:
                signals.files_management_schedule_changed.send(
                    sender=FilesManagementSettings,
                    instance=global_live_settings.files_management
                )


@receiver(post_delete, sender=FilesManagementSettings)
def on_files_management_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.files_management)
        global_live_settings.set_default_files_management_settings()

        if schedule_changed:
            signals.files_management_schedule_changed.send(
                sender=FilesManagementSettings,
                instance=global_live_settings.files_management
            )


@receiver(post_save, sender=AbsenceCalendarSettings)
def on_absence_calendar_settings_saved(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.absence_calendar)
        global_live_settings.set_absence_calendar_settings(instance)

        if schedule_changed:
            signals.absence_calendar_schedule_changed.send(
                sender=AbsenceCalendarSettings,
                instance=global_live_settings.absence_calendar
            )
    else:
        active_absence_calendar_settings = AbsenceCalendarSettings.get_active()

        if not active_absence_calendar_settings:
            schedule_changed = schedule_differs(instance, global_live_settings.absence_calendar)
            global_live_settings.set_default_absence_calendar_settings()

            if schedule_changed:
                signals.absence_calendar_schedule_changed.send(
                    sender=AbsenceCalendarSettings,
                    instance=global_live_settings.absence_calendar
                )


@receiver(post_delete, sender=AbsenceCalendarSettings)
def on_absence_calendar_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.absence_calendar)
        global_live_settings.set_default_absence_calendar_settings()

        if schedule_changed:
            signals.absence_calendar_schedule_changed.send(
                sender=AbsenceCalendarSettings,
                instance=global_live_settings.absence_calendar
            )


@receiver(post_save, sender=NotifierSettings)
def on_notifier_settings_saved(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.notifier)
        global_live_settings.set_notifier_settings(instance)

        if schedule_changed:
            signals.notifier_schedule_changed.send(
                sender=NotifierSettings,
                instance=global_live_settings.notifier
            )
    else:
        active_notifier_settings = NotifierSettings.get_active()

        if not active_notifier_settings:
            schedule_changed = schedule_differs(instance, global_live_settings.notifier)
            global_live_settings.set_default_notifier_settings()

            if schedule_changed:
                signals.notifier_schedule_changed.send(
                    sender=NotifierSettings,
                    instance=global_live_settings.notifier
                )


@receiver(post_delete, sender=NotifierSettings)
def on_notifier_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.notifier)
        global_live_settings.set_default_notifier_settings()

        if schedule_changed:
            signals.notifier_schedule_changed.send(
                sender=NotifierSettings,
                instance=global_live_settings.notifier
            )


@receiver(post_save, sender=ConferenceRoomsSettings)
def on_conference_rooms_settings_saved(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_conference_rooms_settings(instance)
    else:
        active_conference_rooms_settings = ConferenceRoomsSettings.get_active()

        if not active_conference_rooms_settings:
            global_live_settings.set_default_conference_rooms_settings()


@receiver(post_delete, sender=ConferenceRoomsSettings)
def on_conference_rooms_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        global_live_settings.set_default_conference_rooms_settings()


@receiver(post_save, sender=LoggingSettings)
def on_logging_settings_saved(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.logging)
        global_live_settings.set_logging_settings(instance)

        if schedule_changed:
            signals.logging_schedule_changed.send(
                sender=LoggingSettings,
                instance=global_live_settings.logging
            )
    else:
        active_logging_settings = LoggingSettings.get_active()

        if not active_logging_settings:
            schedule_changed = schedule_differs(instance, global_live_settings.logging)
            global_live_settings.set_default_logging_settings()

            if schedule_changed:
                signals.logging_schedule_changed.send(
                    sender=LoggingSettings,
                    instance=global_live_settings.logging
                )


@receiver(post_delete, sender=LoggingSettings)
def on_logging_settings_deleted(sender, instance, **kwargs):
    if instance.active:
        schedule_changed = schedule_differs(instance, global_live_settings.logging)
        global_live_settings.set_default_logging_settings()

        if schedule_changed:
            signals.logging_schedule_changed.send(
                sender=LoggingSettings,
                instance=global_live_settings.logging
            )

