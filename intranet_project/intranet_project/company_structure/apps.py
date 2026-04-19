from django.apps import AppConfig


class CompanyStructureConfig(AppConfig):
    name = 'company_structure'

    def ready(self):
        import company_structure.receivers
