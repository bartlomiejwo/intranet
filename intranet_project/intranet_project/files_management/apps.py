from django.apps import AppConfig


class FilesManagementConfig(AppConfig):
    name = 'files_management'

    def ready(self):
        import files_management.receivers
        from django.conf import settings

        if not settings.MIGRATION_COMMAND:
            from files_management import jobs

            jobs.start()
