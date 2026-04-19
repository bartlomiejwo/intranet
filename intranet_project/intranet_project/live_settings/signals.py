import django.dispatch


glpi_integration_schedule_changed = django.dispatch.Signal()
files_management_schedule_changed = django.dispatch.Signal()
absence_calendar_schedule_changed = django.dispatch.Signal()
notifier_schedule_changed = django.dispatch.Signal()
logging_schedule_changed = django.dispatch.Signal()
