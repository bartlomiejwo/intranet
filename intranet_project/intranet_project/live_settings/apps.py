from django.apps import AppConfig


class LiveSettingsConfig(AppConfig):
    name = 'live_settings'

    def ready(self):
        import live_settings.receivers
        from django.conf import settings

        if not settings.MIGRATION_COMMAND:
            from .global_live_settings import global_live_settings
            global_live_settings.initialize_global_live_settings()
