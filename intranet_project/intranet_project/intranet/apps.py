from django.apps import AppConfig


class IntranetConfig(AppConfig):
    name = 'intranet'

    def ready(self):
        import intranet.receivers
