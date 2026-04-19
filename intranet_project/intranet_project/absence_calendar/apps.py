from django.apps import AppConfig


class AbsenceCalendarConfig(AppConfig):
    name = 'absence_calendar'

    def ready(self):
        import absence_calendar.receivers
        from django.conf import settings

        if not settings.MIGRATION_COMMAND:
            from absence_calendar import jobs

            jobs.start()
