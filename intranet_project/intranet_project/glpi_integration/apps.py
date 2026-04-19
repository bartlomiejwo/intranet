from django.apps import AppConfig


class GlpiIntegrationConfig(AppConfig):
    name = 'glpi_integration'

    def ready(self):
        import glpi_integration.receivers
        from glpi_integration import jobs
        
        jobs.start()
