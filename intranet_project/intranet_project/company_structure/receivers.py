from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import DepartmentMember
from glpi_integration.models import GlpiDepartmentMember, GlpiDepartment, GlpiEmployee
from intranet_project.general_functions import get_object_or_none


@receiver(post_delete, sender=DepartmentMember)
def delete_glpi_department_member_relation(sender, instance, **kwargs):
    glpi_employee = get_object_or_none(GlpiEmployee, employee=instance.employee)
    glpi_department = get_object_or_none(GlpiDepartment, department=instance.department)

    if glpi_employee is not None and glpi_department is not None:
        GlpiDepartmentMember.objects.filter(
            glpi_department=glpi_department,
            glpi_employee=glpi_employee,
        ).delete()

