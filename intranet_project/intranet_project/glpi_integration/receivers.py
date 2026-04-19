from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver

from .models import GlpiDepartment, GlpiSubordinateDepartment, GlpiDepartmentMember
from company_structure.models import SubordinateDepartment, DepartmentMember
from intranet_project import general_functions
from live_settings import signals
from live_settings.models import GlpiIntegrationSettings
from . import jobs


@receiver(post_save, sender=GlpiDepartment)
def create_department(sender, instance, created, **kwargs):
    if not created:
        instance.department.save()


@receiver(post_delete, sender=GlpiDepartment)
def delete_department(sender, instance, **kwargs):
    instance.department.delete()


@receiver(post_save, sender=GlpiSubordinateDepartment)
def create_subordinate_department_relation(sender, instance, created, **kwargs):
    if created:
        SubordinateDepartment.objects.create(
            subordinate_department=instance.glpi_subordinate_department.department,
            parent_department=instance.glpi_parent_department.department,
        )


@receiver(pre_delete, sender=GlpiSubordinateDepartment)
def delete_subordinate_department_relation(sender, instance, **kwargs):
    SubordinateDepartment.objects.filter(
        subordinate_department=instance.glpi_subordinate_department.department,
        parent_department=instance.glpi_parent_department.department
    ).delete()


@receiver(post_save, sender=GlpiDepartmentMember)
def create_or_update_department_member_relation(sender, instance, created, **kwargs):
    if created:
        DepartmentMember.objects.create(
            department=instance.glpi_department.department,
            employee=instance.glpi_employee.employee,
            role=instance.role
        )
    else:
        department_member = general_functions.get_object_or_none(
                                DepartmentMember, 
                                department=instance.glpi_department.department,
                                employee=instance.glpi_employee.employee
                            )

        if department_member:
            department_member.role = instance.role
            department_member.save()


@receiver(pre_delete, sender=GlpiDepartmentMember)
def delete_department_member_relation(sender, instance, **kwargs):
    DepartmentMember.objects.filter(
        department=instance.glpi_department.department,
        employee=instance.glpi_employee.employee,
    ).delete()


@receiver(signals.glpi_integration_schedule_changed, sender=GlpiIntegrationSettings)
def on_glpi_integration_settings_changed(sender, instance, **kwargs):
    jobs.reschedule_company_structure_sync()
