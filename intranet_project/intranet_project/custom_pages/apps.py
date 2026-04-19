from django.apps import AppConfig


class CustomPagesConfig(AppConfig):
    name = 'custom_pages'

    def ready(self):
        import custom_pages.receivers
