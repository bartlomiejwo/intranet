from django.contrib import admin
from .models import (
        GeneralSettings, CompanySettings, GlpiIntegrationSettings,
        FilesManagementSettings, AbsenceCalendarSettings,
        NotifierSettings, ConferenceRoomsSettings, UsefulLink,
        LoggingSettings,
    )


class GeneralSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class GlpiIntegrationSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class FilesManagementSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class AbsenceCalendarSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class NotifierSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class ConferenceRoomsSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


class UsefulLinksAdmin(admin.ModelAdmin):
    list_display = ['name',]
    ordering = ['position', 'name',]


class LoggingSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'active',]
    ordering = ['-active', 'name',]


admin.site.register(GeneralSettings, GeneralSettingsAdmin)
admin.site.register(CompanySettings, CompanySettingsAdmin)
admin.site.register(GlpiIntegrationSettings, GlpiIntegrationSettingsAdmin)
admin.site.register(FilesManagementSettings, FilesManagementSettingsAdmin)
admin.site.register(AbsenceCalendarSettings, AbsenceCalendarSettingsAdmin)
admin.site.register(NotifierSettings, NotifierSettingsAdmin)
admin.site.register(ConferenceRoomsSettings, ConferenceRoomsSettingsAdmin)
admin.site.register(UsefulLink, UsefulLinksAdmin)
admin.site.register(LoggingSettings, LoggingSettingsAdmin)
