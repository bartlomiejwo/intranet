from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    name = 'scheduler'

    def ready(self):
        import scheduler.receivers
        from django.conf import settings
        from scheduler import jobs

        if not settings.MIGRATION_COMMAND:
            import scheduler.jobs_scheduler

        jobs.start()
