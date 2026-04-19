from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext
from intranet_project import general_functions
from django.db.models import Q

from absence_calendar import models as absence_calendar_models


class Department(models.Model):
    class Meta:
        verbose_name = _('department')
        verbose_name_plural = _('departments')

    name = models.CharField(max_length=250, verbose_name=_('name'))

    def get_subordinate_departments(self):
        subordinate_departments_relations = SubordinateDepartment.objects.select_related(
            'subordinate_department').filter(parent_department=self)

        return [x.subordinate_department for x in subordinate_departments_relations]

    @staticmethod
    def get_all_subordinate_departments(department, all_subordinate_departments):
        all_subordinate_departments.append(department)
        closest_subordinate_departments = department.get_subordinate_departments()

        if closest_subordinate_departments:
            for subordinate_department in closest_subordinate_departments:
                Department.get_all_subordinate_departments(subordinate_department, all_subordinate_departments)

    def get_parent_departments(self):
        parent_departments_relations = SubordinateDepartment.objects.select_related(
            'parent_department').filter(subordinate_department=self)
        
        return [x.parent_department for x in parent_departments_relations]

    @staticmethod
    def get_all_departments_in_hierarchy(department, departments_in_hierarchy):
        departments_in_hierarchy.append(department)
        parent_departments = department.get_parent_departments()

        if parent_departments:
            for parent_department in parent_departments:
                Department.get_all_departments_in_hierarchy(parent_department, departments_in_hierarchy)

    @staticmethod
    def get_employee_ids_who_are_members_of_department(department_id):
        departments = Department.objects.filter(id=department_id)
        department_members = DepartmentMember.objects.filter(department__in=departments)

        return [x.employee.id for x in department_members]

    def __str__(self):
        return self.name


class SubordinateDepartment(models.Model):
    class Meta:
        verbose_name = _('subordinate department')
        verbose_name_plural = _('departments')

    subordinate_department = models.ForeignKey(Department, related_name='SubordinateDepartment',
                                                on_delete=models.CASCADE, verbose_name=_('subordinate department'))
    parent_department = models.ForeignKey(Department, related_name='ParentDepartment',
                                            on_delete=models.CASCADE, verbose_name=_('parent department'))

    def __str__(self):
        return self.subordinate_department.name

    def clean(self):
        self.validate_relation_with_itself()
    
    def validate_relation_with_itself(self):
        if self.subordinate_department == self.parent_department:
            raise ValidationError(
                    _('Department cannot be a subordinate of itself.'),
                    code='department_cannot_be_a_subordinate_of_itself',
                )


class Employee(models.Model):
    class Meta:
        verbose_name = _('employee')
        verbose_name_plural = _('employees')

        permissions = (
            ('can_fill_employee_additional_data', 'Can fill additional employee data'),
        )

    user = models.OneToOneField(User, related_name='employee', on_delete=models.CASCADE,
                                verbose_name=_('user'))
    cell_phone_number = models.CharField(max_length=15, blank=True, verbose_name=_('cell phone number'))
    internal_phone_number = models.CharField(max_length=15, blank=True, verbose_name=_('internal phone number'))
    additional_phone_number = models.CharField(max_length=15, blank=True, verbose_name=_('additional phone number'))
    title = models.CharField(max_length=100, blank=True, verbose_name=pgettext('title', 'job title'))
    location = models.CharField(max_length=100, blank=True, verbose_name=_('location'))
    registration_number = models.CharField(max_length=20, blank=True, verbose_name=_('registration number'))
    region_name = models.CharField(max_length=250, blank=True, default='', verbose_name=_('region name'))
    region_code = models.CharField(max_length=15, blank=True, default='', verbose_name=_('region code'))
    cities = models.CharField(max_length=1000, blank=True, default='', verbose_name=_('cities'))
    short_cell_phone_number = models.CharField(max_length=5, blank=True, default='',
                                                verbose_name=_('short cell phone number'))

    def get_supervisor_users_ids(self):
        employee_memberships = DepartmentMember.objects.select_related('employee').filter(employee=self)
        departments = []

        for employee_membership in employee_memberships:
            hierarchy_departments = []
            Department.get_all_departments_in_hierarchy(employee_membership.department, hierarchy_departments)
            departments += hierarchy_departments

        departments = general_functions.get_list_of_objects_without_duplicates(departments, lambda x: x.name)
        departments_ids = [x.id for x in departments]

        supervisor_employees = DepartmentMember.objects.filter(
            Q(employee__user__is_active=True),
            Q(department__in=departments),
            Q(role=DepartmentMember.MANAGER_ROLE) |
            Q(role=DepartmentMember.DEPUTY_MANAGER_ROLE)
        )

        return [x.employee.user.id for x in supervisor_employees if x.employee != self]

    def get_subordinate_users_ids(self):
        if not (self.is_deputy_manager() or self.is_manager()):
            return None
        
        employee_memberships = DepartmentMember.objects.select_related('employee').filter(employee=self)
        departments = []

        for employee_membership in employee_memberships:
            subordinate_departments = []
            Department.get_all_subordinate_departments(employee_membership.department, subordinate_departments)
            departments += subordinate_departments

        departments = general_functions.get_list_of_objects_without_duplicates(departments, lambda x: x.name)
        departments_ids = [x.id for x in departments]

        subordinate_employees = DepartmentMember.objects.filter(
            Q(employee__user__is_active=True),
            Q(department__in=departments),
        )

        return [x.employee.user.id for x in subordinate_employees if x.employee != self]

    def get_department(self):
        member = general_functions.get_object_or_none(DepartmentMember, employee=self)

        return member.department if member else None
    
    def get_department_name(self):
        department = self.get_department()

        return department.name if department else ''

    def get_department_manager(self):
        department = self.get_department()

        if department is None:
            return None

        department_manager = general_functions.get_object_or_none(
                                DepartmentMember,
                                department=department,
                                role=DepartmentMember.MANAGER_ROLE
                            )
        
        if department_manager:
            return department_manager.employee
        
        return None

    def get_department_manager_name(self):
        manager = self.get_department_manager()

        return manager.user.profile.get_name() if manager else ''

    def is_manager(self):
        department = self.get_department()

        is_manager = general_functions.get_object_or_none(
            DepartmentMember,
            employee=self,
            department=department,
            role=DepartmentMember.MANAGER_ROLE
        )

        return True if is_manager else None

    def is_deputy_manager(self):
        department = self.get_department()

        is_deputy_manager = general_functions.get_object_or_none(
            DepartmentMember,
            employee=self,
            department=department,
            role=DepartmentMember.DEPUTY_MANAGER_ROLE
        )

        return True if is_deputy_manager else None
    
    def get_section(self):
        department = self.get_department()
        
        if not department:
            return ''

        if 'Pion' in department.name:
            return department.name
        
        hierarchy_departments = []
        Department.get_all_departments_in_hierarchy(department, hierarchy_departments)

        for hierarchy_department in hierarchy_departments:
            if 'Pion' in hierarchy_department.name:
                return hierarchy_department.name
        
        return ''

    def get_cell_phone_number(self):
        return Employee.clean_phone_number(self.cell_phone_number)

    def get_internal_phone_number(self):
        return Employee.clean_phone_number(self.internal_phone_number)

    def get_additional_phone_number(self):
        return Employee.clean_phone_number(self.additional_phone_number)

    def get_todays_absence(self):
        today = timezone.localtime(timezone.now()).date()

        vacation_leaves = absence_calendar_models.VacationLeave.objects.filter(
            absent=self.user,
            start_date__lte=today,
            end_date__gte=today,
            status__in=(
                absence_calendar_models.VacationLeave.ACCEPTED_STATUS,
                absence_calendar_models.VacationLeave.PENDING_TO_CANCEL_STATUS,
                absence_calendar_models.VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS
            )
        )

        if vacation_leaves:
            return vacation_leaves.first()

        absences = absence_calendar_models.Absence.objects.filter(
            absent=self.user,
            start_date__lte=today,
            end_date__gte=today
        )

        if absences:
            return absences.first()

        special_leaves = absence_calendar_models.SpecialLeave.objects.filter(
            absent=self.user,
            start_date__lte=today,
            end_date__gte=today,
            status__in=(
                absence_calendar_models.SpecialLeave.ACCEPTED_STATUS,
                absence_calendar_models.SpecialLeave.PENDING_TO_CANCEL_STATUS,
                absence_calendar_models.SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS,
                absence_calendar_models.SpecialLeave.CONFIRMED_STATUS
            )
        )

        if special_leaves:
            return special_leaves.first()

        return None

    def is_absent_today(self):
        return True if self.get_todays_absence() else False

    def is_on_remote_work_today(self):
        today = timezone.localtime(timezone.now()).date()

        remote_works = absence_calendar_models.RemoteWork.objects.filter(
            absent=self.user,
            start_date__lte=today,
            end_date__gte=today,
            status__in=(
                absence_calendar_models.RemoteWork.ACCEPTED_STATUS,
                absence_calendar_models.RemoteWork.PENDING_TO_CANCEL_STATUS,
                absence_calendar_models.RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS
            )
        )

        return True if remote_works else False
    
    @staticmethod
    def clean_phone_number(phone_number):
        try:
            cleaned_phone_number = f'{phone_number[:3]} {phone_number[3:6]} {phone_number[6:9]} {phone_number[9:]}'
        except IndexError as e:
            return phone_number
        else:
            return cleaned_phone_number

    def __str__(self):
        return _('Employee') + ' ' + self.user.profile.get_name()

    @staticmethod
    def fill_query_search_args_phone(args, phone_number):
        query = (
            Q(cell_phone_number__icontains=phone_number) |
            Q(internal_phone_number__icontains=phone_number) |
            Q(additional_phone_number__icontains=phone_number) |
            Q(short_cell_phone_number__icontains=phone_number)
        )

        args.append(query)


class DepartmentMember(models.Model):
    class Meta:
        verbose_name = _('department member')
        verbose_name_plural = _('department members')

    MEMBER_ROLE = 1
    DEPUTY_MANAGER_ROLE = 2
    MANAGER_ROLE = 3

    ROLE_CHOICES = (
        (MEMBER_ROLE, _('Member')),
        (DEPUTY_MANAGER_ROLE, _('Deputy Manager')),
        (MANAGER_ROLE, _('Manager')),
    )

    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_('department'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('employee'))
    role = models.IntegerField(choices=ROLE_CHOICES, default=MEMBER_ROLE, verbose_name=_('role'))

    def __str__(self):
        return f'{self.department.name} - {self.employee.user.username}'

    @staticmethod
    def get_role_representation(role):
        for role_choice in DepartmentMember.ROLE_CHOICES:
            if role_choice[0] == role:
                return role_choice[1]

        raise ValueError(_('Wrong department member role was given.'))
