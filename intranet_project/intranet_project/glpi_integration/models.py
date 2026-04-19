from django.db import models
from company_structure.models import Department, Employee
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class GlpiDepartment(models.Model):
    class Meta:
        verbose_name = _('GLPI department')
        verbose_name_plural = _('GLPI departments')

    glpi_group_id = models.PositiveIntegerField(unique=True, verbose_name=_('GLPI group ID'))
    glpi_last_modification_date = models.CharField(max_length=50, verbose_name=_('GLPI last modification date'))

    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_('department'))

    def __str__(self):
        return 'GLPI ' + self.department.name


class GlpiSubordinateDepartment(models.Model):
    class Meta:
        verbose_name = _('GLPI subordinate department')
        verbose_name_plural = _('GLPI subordinate departments')

    glpi_subordinate_department = models.ForeignKey(
        GlpiDepartment, 
        related_name='GlpiSubordinateDepartment',
        on_delete=models.CASCADE,
        verbose_name=_('GLPI subordinate department')
    )
    glpi_parent_department = models.ForeignKey(
        GlpiDepartment,
        related_name='GlpiParentDepartment',
        on_delete=models.CASCADE,
        verbose_name=_('GLPI parent department')
    )

    def __str__(self):
        return 'GLPI ' + self.glpi_subordinate_department.department.name
    
    def clean(self):
        self.validate_relation_with_itself()
    
    def validate_relation_with_itself(self):
        if self.glpi_subordinate_department == self.glpi_parent_department:
            raise ValidationError(
                    _('Glpi department cannot be a subordinate of itself.'),
                    code='glpi_department_cannot_be_a_subordinate_of_itself',
                )


class GlpiEmployee(models.Model):
    class Meta:
        verbose_name = _('GLPI employee')
        verbose_name_plural = _('GLPI employees')

    glpi_user_id = models.PositiveIntegerField(unique=True, verbose_name=_('GLPI user ID'))
    glpi_last_modification_date = models.CharField(max_length=50, verbose_name=_('GLPI last modification date'))

    employee = models.OneToOneField(Employee, related_name='glpi_employee',
                                    on_delete=models.CASCADE, verbose_name=_('employee'))

    def __str__(self):
        return 'GLPI ' + str(self.employee)


class GlpiDepartmentMember(models.Model):
    class Meta:
        verbose_name = _('GLPI deparment member')
        verbose_name_plural = _('GLPI department members')

    MEMBER_ROLE = 1
    DEPUTY_MANAGER_ROLE = 2
    MANAGER_ROLE = 3

    ROLE_CHOICES = (
        (MEMBER_ROLE, _('Member')),
        (DEPUTY_MANAGER_ROLE, _('Deputy Manager')),
        (MANAGER_ROLE, _('Manager')),
    )

    glpi_relation_id = models.PositiveIntegerField(unique=True, verbose_name=_('GLPI relation ID'))
    glpi_department = models.ForeignKey(GlpiDepartment, on_delete=models.CASCADE,
                                        verbose_name=_('GLPI department'))
    glpi_employee = models.ForeignKey(GlpiEmployee, on_delete=models.CASCADE, verbose_name=_('GLPI employee'))
    role = models.IntegerField(choices=ROLE_CHOICES, default=MEMBER_ROLE, verbose_name=_('GLPI role'))
    
    def __str__(self):
        return f'{str(self.glpi_department)} - {str(self.glpi_employee)}'
