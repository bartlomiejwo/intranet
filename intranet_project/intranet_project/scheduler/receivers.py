from django.dispatch import receiver

from live_settings.models import LoggingSettings
from live_settings import signals as live_settings_signals
from . import jobs


@receiver(live_settings_signals.logging_schedule_changed, sender=LoggingSettings)
def on_logging_settings_changed(sender, instance, **kwargs):
    jobs.reschedule_removing_logs()