import logging

from .models import GlpiDepartment, GlpiSubordinateDepartment, GlpiEmployee, GlpiDepartmentMember
from company_structure.models import Department, SubordinateDepartment, Employee
from django.contrib.auth.models import User
from intranet_project import general_functions
from django.db import transaction
from django.utils.translation import gettext_lazy as _
import glpi_integration.jobs as glpi_integration_jobs
from intranet_project import general_functions


logger = logging.getLogger(__name__)


class CompanyStructureUpdater:

    def __init__(self):
        pass

    @staticmethod
    def synchronize_glpi_departments(glpi_groups):
        glpi_departments = GlpiDepartment.objects.all().order_by('glpi_group_id')

        CompanyStructureUpdater.handle_new_glpi_departments(glpi_departments, glpi_groups)
        CompanyStructureUpdater.handle_existing_glpi_departments(glpi_departments, glpi_groups)

    @staticmethod
    def handle_new_glpi_departments(glpi_departments, glpi_groups):
        for glpi_group in glpi_groups:
            found = general_functions.binary_search(glpi_departments, glpi_group.id,
                                            lambda glpi_department: glpi_department.glpi_group_id)

            if not found:
                CompanyStructureUpdater.create_glpi_department(glpi_group)
    
    @staticmethod
    def handle_existing_glpi_departments(glpi_departments, glpi_groups):
        for glpi_department in glpi_departments:
            found = general_functions.binary_search(glpi_groups, glpi_department.glpi_group_id,
                                                    lambda glpi_group: glpi_group.id)

            if found:
                CompanyStructureUpdater.update_glpi_department(glpi_department, found)
            else:
                glpi_department.delete()

    @staticmethod
    @transaction.atomic
    def create_glpi_department(glpi_group):
        department = Department.objects.create(name=glpi_group.name)
        glpi_department = GlpiDepartment.objects.create(
            glpi_group_id=glpi_group.id, 
            glpi_last_modification_date=glpi_group.date_mod,
            department=department
        )
        
        CompanyStructureUpdater.create_glpi_department_parent_relations(glpi_department, glpi_group)

    @staticmethod
    @transaction.atomic
    def update_glpi_department(glpi_department, glpi_group):
        if glpi_department.glpi_last_modification_date != glpi_group.date_mod:
            glpi_department.glpi_group_id = glpi_group.id
            glpi_department.glpi_last_modification_date = glpi_group.date_mod
            glpi_department.department.name = glpi_group.name
            glpi_department.save()

        CompanyStructureUpdater.update_glpi_department_parent_relations(glpi_department, glpi_group)

    @staticmethod
    def update_glpi_department_parent_relations(glpi_department, glpi_group):
        glpi_department_parent_relations = GlpiSubordinateDepartment.objects.filter(
            glpi_subordinate_department=glpi_department).order_by('glpi_parent_department__id')

        CompanyStructureUpdater.handle_existing_glpi_department_parent_relations(
            glpi_department_parent_relations, 
            glpi_group
        )

        CompanyStructureUpdater.handle_new_glpi_department_parent_relations(
            glpi_department,
            glpi_department_parent_relations,
            glpi_group
        )

    @staticmethod
    def handle_existing_glpi_department_parent_relations(glpi_department_parent_relations, glpi_group):
        for glpi_department_parent_relation in glpi_department_parent_relations:
            if not glpi_department_parent_relation.glpi_parent_department.glpi_group_id \
                in glpi_group.get_closest_parents_list():
                glpi_department_parent_relation.delete()

    @staticmethod
    def handle_new_glpi_department_parent_relations(glpi_department, glpi_department_parent_relations, glpi_group):
        for glpi_group_id in glpi_group.get_closest_parents_list():
            found = general_functions.binary_search(
                glpi_department_parent_relations, 
                glpi_group_id,
                lambda glpi_subordinate_relation: glpi_subordinate_relation.glpi_parent_department.glpi_group_id
            )
            
            if not found:
                CompanyStructureUpdater.create_glpi_department_parent_relations(
                    glpi_department,
                    glpi_group
                )
    
    @staticmethod
    def create_glpi_department_parent_relations(glpi_department, glpi_group):
        for glpi_group_id in glpi_group.get_closest_parents_list():
            CompanyStructureUpdater.create_glpi_department_parent_relation(
                glpi_department,
                glpi_group_id
            )

    @staticmethod
    def create_glpi_department_parent_relation(glpi_department, glpi_group_id):
        glpi_parent_department = general_functions.get_object_or_none(
            GlpiDepartment,
            glpi_group_id=glpi_group_id
        )

        if glpi_parent_department:
            GlpiSubordinateDepartment.objects.create(
                glpi_subordinate_department=glpi_department,
                glpi_parent_department=glpi_parent_department
            )
        else:
            general_functions.log_job_warning(logger, glpi_integration_jobs.get_company_structure_sync_job_id(), 
                _('GLPI parent department of %(id)d glpi department does not exist.') % {'id': glpi_group_id})

    @staticmethod
    def synchronize_glpi_users(glpi_users):
        users = User.objects.all().order_by('username')
        glpi_employees = GlpiEmployee.objects.all().order_by('glpi_user_id')
        
        CompanyStructureUpdater.synchronize_users_active_status(glpi_employees, glpi_users)
        glpi_employees_departments_relations = CompanyStructureUpdater.get_glpi_employees_departments_relations()

        for glpi_user in glpi_users:
            glpi_employee_departments_relations = CompanyStructureUpdater.get_glpi_employee_departments_relations(
                                                                    glpi_user, glpi_employees_departments_relations)
            
            CompanyStructureUpdater.synchronize_glpi_user(glpi_user, users, glpi_employees,
                                                            glpi_employee_departments_relations)

    @staticmethod
    def synchronize_users_active_status(glpi_employees, glpi_users):
        for glpi_employee in glpi_employees:
            glpi_user_found = general_functions.binary_search(glpi_users, glpi_employee.glpi_user_id,
                                                                    lambda glpi_user: glpi_user.id)
            
            if glpi_user_found:
                if glpi_user_found.active:
                    if not glpi_employee.employee.user.is_active:
                        glpi_employee.employee.user.is_active = True
                        glpi_employee.employee.user.save()
                else:
                    if glpi_employee.employee.user.is_active:
                        glpi_employee.employee.user.is_active = False
                        glpi_employee.employee.user.save()
            else:
                glpi_employee.employee.user.is_active = False
                glpi_employee.employee.user.save()
            
    @staticmethod
    def get_glpi_employees_departments_relations():
        glpi_department_members = GlpiDepartmentMember.objects.select_related('glpi_department', 'glpi_employee')
        glpi_employees_departments_relations = []

        for glpi_department_member in glpi_department_members:
            glpi_employee_index = next((i for i,d in enumerate(glpi_employees_departments_relations) if 
                            str(glpi_department_member.glpi_employee.glpi_user_id) in d), None)

            if glpi_employee_index is not None:
                glpi_employees_departments_relations[glpi_employee_index] \
                    [str(glpi_department_member.glpi_employee.glpi_user_id)].append(glpi_department_member)
            else:
                employee_departments = {
                    str(glpi_department_member.glpi_employee.glpi_user_id): [glpi_department_member,],
                }
                glpi_employees_departments_relations.append(employee_departments)
        
        return glpi_employees_departments_relations

    @staticmethod
    def get_glpi_employee_departments_relations(glpi_user, glpi_employees_departments_relations):
        glpi_employee_index = next((i for i,d in enumerate(glpi_employees_departments_relations) if 
                                    str(glpi_user.id) in d), None)

        if glpi_employee_index is None:
            return []
        else:
            return glpi_employees_departments_relations[glpi_employee_index][str(glpi_user.id)]

    @staticmethod
    def synchronize_glpi_user(glpi_user, users, glpi_employees, glpi_employee_departments_relations):
        try:
            user_created = CompanyStructureUpdater.handle_user_creation(glpi_user, users, glpi_employees)
        except UsernameOccupied as e:
            general_functions.log_job_warning(logger, glpi_integration_jobs.get_company_structure_sync_job_id(),
                _('This nickname is already taken, given account (%(account_name)d) will ' + \
                'not be synchronized.') % {'id': str(e)})
        else:
            CompanyStructureUpdater.handle_user_update(glpi_user, user_created, users, glpi_employees,
                                                        glpi_employee_departments_relations)

    @staticmethod
    def handle_user_creation(glpi_user, users, glpi_employees):
        user_created = None

        if glpi_user.create_user:
            glpi_employee_found = general_functions.binary_search(glpi_employees, glpi_user.id,
                                lambda glpi_employee: glpi_employee.glpi_user_id)

            if glpi_employee_found:
                CompanyStructureUpdater.handle_user_creation_when_glpi_employee_exists(glpi_user, 
                                                                        glpi_employee_found, users)
            else:
                user_created = CompanyStructureUpdater.handle_user_creation_when_glpi_employee_does_not_exist(
                                                                                            glpi_user, users)
        
        return user_created
    
    @staticmethod
    def handle_user_creation_when_glpi_employee_exists(glpi_user, glpi_employee, users):
        user = glpi_employee.employee.user

        if user.username != glpi_user.name:
            user_found = general_functions.binary_search(users, glpi_user.name, lambda user: user.username)

            if not user_found:
                user.username = glpi_user.name
                user.save()
            else:
                raise UsernameOccupied(user.username)
    
    @staticmethod
    def handle_user_creation_when_glpi_employee_does_not_exist(glpi_user, users):
        user_found = general_functions.binary_search(users, glpi_user.name, lambda user: user.username)

        if not user_found:
            return User.objects.create_user(
                username=glpi_user.name,
                password=general_functions.get_random_password(32),
            )
        else:
            return None

    @staticmethod
    def handle_user_update(glpi_user, user_created, users, glpi_employees, glpi_employee_departments_relations):
        glpi_employee_found = general_functions.binary_search(glpi_employees, glpi_user.id,
                                            lambda glpi_employee: glpi_employee.glpi_user_id)

        if glpi_employee_found:
            CompanyStructureUpdater.handle_user_update_when_glpi_employee_exists(glpi_user, 
                            glpi_employee_found, users, glpi_employee_departments_relations)
        else:
            CompanyStructureUpdater.handle_user_update_when_glpi_employee_does_not_exist(
                        glpi_user, user_created, users, glpi_employee_departments_relations)

    @staticmethod
    def handle_user_update_when_glpi_employee_exists(glpi_user, glpi_employee, users, glpi_employee_departments_relations):
        force_update = False
        employee = glpi_employee.employee

        if employee.user.username != glpi_user.name:
            force_update = True
            CompanyStructureUpdater.replace_user_in_employee(glpi_user, employee, users)

        if force_update or glpi_employee.glpi_last_modification_date != glpi_user.date_mod:
            CompanyStructureUpdater.update_user_when_glpi_employee_exists(glpi_user, 
                                                            glpi_employee, employee)
        
        CompanyStructureUpdater.synchronize_glpi_employee_departments(glpi_employee, glpi_user.user_groups,
                                                                    glpi_employee_departments_relations)

    @staticmethod
    @transaction.atomic
    def replace_user_in_employee(glpi_user, employee, users):
        employee.user.is_active = False
        employee.user.save()
        user_found = general_functions.binary_search(users, glpi_user.name, lambda user: user.username)

        if user_found:
            employee.user = user_found
        else:
            employee.user = User.objects.create_user(
                username=glpi_user.name,
                password=general_functions.get_random_password(32),
            )

    @staticmethod
    @transaction.atomic
    def update_user_when_glpi_employee_exists(glpi_user, glpi_employee, employee):
        employee.cell_phone_number=glpi_user.mobile
        employee.internal_phone_number=glpi_user.phone
        employee.additional_phone_number=glpi_user.phone2
        employee.title=glpi_user.title
        employee.location=glpi_user.location
        employee.registration_number=glpi_user.registration_number

        if glpi_user.sync_comment_data:
            CompanyStructureUpdater.fill_employee_comment_data(employee, glpi_user)

        employee.save()

        user = employee.user
        user.first_name = glpi_user.firstname
        user.last_name = glpi_user.realname
        user.email = glpi_user.email
        user.save()

        glpi_employee.glpi_last_modification_date = glpi_user.date_mod
        glpi_employee.save()

    @staticmethod
    def handle_user_update_when_glpi_employee_does_not_exist(glpi_user, user_created, users, glpi_employee_departments_relations):
        if user_created:
            user_found = user_created
        else:
            user_found = general_functions.binary_search(users, glpi_user.name, lambda user: user.username)

        if user_found:
            employee_found = general_functions.get_related_object_or_none(user_found, Employee, 'employee')

            if employee_found:
                CompanyStructureUpdater.update_user_when_employee_exists(glpi_user, employee_found, user_found,
                                                                        glpi_employee_departments_relations)
            else:
                CompanyStructureUpdater.update_user_when_employee_does_not_exist(glpi_user, user_found,
                                                                    glpi_employee_departments_relations)

    @staticmethod
    @transaction.atomic
    def update_user_when_employee_exists(glpi_user, employee, user, glpi_employee_departments_relations):
        CompanyStructureUpdater.clear_glpi_employee(employee)

        glpi_employee = GlpiEmployee.objects.create(
            glpi_user_id=glpi_user.id,
            glpi_last_modification_date=glpi_user.date_mod,
            employee=employee
        )

        employee.cell_phone_number=glpi_user.mobile
        employee.internal_phone_number=glpi_user.phone
        employee.additional_phone_number=glpi_user.phone2
        employee.title=glpi_user.title
        employee.location=glpi_user.location
        employee.registration_number=glpi_user.registration_number

        if glpi_user.sync_comment_data:
            CompanyStructureUpdater.fill_employee_comment_data(employee, glpi_user)

        employee.save()

        user.first_name = glpi_user.firstname
        user.last_name = glpi_user.realname
        user.email = glpi_user.email

        if glpi_user.active:
            if not user.is_active:
                user.is_active = True
        else:
            if user.is_active:
                user.is_active = False

        user.save()
        CompanyStructureUpdater.synchronize_glpi_employee_departments(glpi_employee, glpi_user.user_groups,
                                                                    glpi_employee_departments_relations)

    @staticmethod
    def clear_glpi_employee(employee):
        has_glpi_employee = general_functions.get_related_object_or_none(employee, GlpiEmployee, 'glpi_employee')

        if has_glpi_employee:
            has_glpi_employee.delete()

    @staticmethod
    @transaction.atomic
    def update_user_when_employee_does_not_exist(glpi_user, user, glpi_employee_departments_relations):
        employee = Employee.objects.create(
            user=user, 
            cell_phone_number=glpi_user.mobile, 
            internal_phone_number=glpi_user.phone, 
            additional_phone_number=glpi_user.phone2, 
            title=glpi_user.title, 
            location=glpi_user.location, 
            registration_number=glpi_user.registration_number
        )

        if glpi_user.sync_comment_data:
            CompanyStructureUpdater.fill_employee_comment_data(employee, glpi_user)
            employee.save()

        glpi_employee = GlpiEmployee.objects.create(
            glpi_user_id=glpi_user.id,
            glpi_last_modification_date=glpi_user.date_mod,
            employee=employee
        )

        user.first_name = glpi_user.firstname
        user.last_name = glpi_user.realname
        user.email = glpi_user.email
        user.save()

        CompanyStructureUpdater.synchronize_glpi_employee_departments(glpi_employee, glpi_user.user_groups,
                                                                    glpi_employee_departments_relations)

    @staticmethod
    def fill_employee_comment_data(employee, glpi_user):
        if glpi_user.sync_region_name:
            employee.region_name = glpi_user.region_name

        if glpi_user.sync_region_code:
            employee.region_code = glpi_user.region_code

        if glpi_user.sync_cities:
            employee.cities = glpi_user.cities

        if glpi_user.sync_short_cell_phone_number:
            employee.short_cell_phone_number = glpi_user.short_cell_phone_number

    @staticmethod
    def synchronize_glpi_employee_departments(glpi_employee, glpi_user_groups, glpi_employee_departments_relations):
        CompanyStructureUpdater.refresh_glpi_employee_department_relations(glpi_employee, 
                                    glpi_user_groups, glpi_employee_departments_relations)

        CompanyStructureUpdater.delete_glpi_employee_department_relations(glpi_user_groups,
                                                        glpi_employee_departments_relations)

    @staticmethod
    def refresh_glpi_employee_department_relations(glpi_employee, glpi_user_groups, glpi_employee_departments_relations):
        for glpi_user_group in glpi_user_groups:
            found = next((x for x in glpi_employee_departments_relations \
                            if x.glpi_department.glpi_group_id == glpi_user_group.group_id), None)

            if found:
                CompanyStructureUpdater.update_glpi_employee_department_relation(glpi_user_group, found)
            else:
                CompanyStructureUpdater.create_glpi_employee_department_relation(glpi_user_group, glpi_employee)

    @staticmethod
    def create_glpi_employee_department_relation(glpi_user_group, glpi_employee):
        glpi_department = general_functions.get_object_or_none(GlpiDepartment, glpi_group_id=glpi_user_group.group_id)

        if glpi_department is not None:
            GlpiDepartmentMember.objects.create(
                glpi_relation_id=glpi_user_group.relation_id,
                glpi_department=glpi_department,
                glpi_employee=glpi_employee,
                role=glpi_user_group.role
            )
    
    @staticmethod
    def update_glpi_employee_department_relation(glpi_user_group, glpi_employee_department_relation):
        if glpi_user_group.role != glpi_employee_department_relation.role:
            glpi_employee_department_relation.role = glpi_user_group.role
            glpi_employee_department_relation.save()

    @staticmethod
    def delete_glpi_employee_department_relations(glpi_user_groups, glpi_employee_departments_relations):
        glpi_user_groups_ids = [x.group_id for x in glpi_user_groups]

        for glpi_employee_departments_relation in glpi_employee_departments_relations:
            if glpi_employee_departments_relation.glpi_department.glpi_group_id not in glpi_user_groups_ids:
                glpi_employee_departments_relation.delete()


class UsernameOccupied(Exception):
    pass
