import json
import logging
from datetime import datetime

from django.utils import timezone

from intranet_project.api_integration_service import ApiIntegrationService
from company_structure.models import DepartmentMember
from django.utils.translation import gettext_lazy as _
import glpi_integration.jobs as glpi_integration_jobs
from intranet_project import general_functions


logger = logging.getLogger(__name__)


class GlpiGroup:

    def __init__(self, id, name, date_mod, level, parent_groups_ids):
        self.id = id
        self.name = name
        self.date_mod = date_mod
        self.level = level
        self.parent_groups_ids = parent_groups_ids
    
    def get_closest_parents_list(self):
        return self.parent_groups_ids[-1:]

    def __str__(self):
        return f'ID: {self.id} NAME: {self.name} LAST MODIFICATION DATE: {self.date_mod} LEVEL: {self.level} ' + \
                f'PARENT GROUPS IDS: {self.parent_groups_ids}'


class GlpiUser:
    
    def __init__(self, id, date_mod, active, name, realname, firstname, phone, phone2, mobile, email, title, location, 
                registration_number, create_user):
        self.id = id
        self.date_mod = date_mod
        self.active = active
        self.name = name
        self.realname = realname
        self.firstname = firstname
        self.phone = phone
        self.phone2 = phone2
        self.mobile = mobile
        self.email = email
        self.title = title
        self.location = location
        self.registration_number = registration_number
        self.create_user = create_user
        self.user_groups = []

        self.sync_comment_data = False

        self.sync_region_name = False
        self.region_name = ''

        self.sync_region_code = False
        self.region_code = ''

        self.sync_cities = False
        self.cities = ''

        self.sync_short_cell_phone_number = False
        self.short_cell_phone_number = ''

    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, active):
        self.__active = True if active else False

    @property
    def realname(self):
        return self.__realname

    @realname.setter
    def realname(self, realname):
        self.__realname = realname if realname is not None else ''
    
    @property
    def firstname(self):
        return self.__firstname

    @firstname.setter
    def firstname(self, firstname):
        self.__firstname = firstname if firstname is not None else ''
    
    @property
    def phone(self):
        return self.__phone

    @phone.setter
    def phone(self, phone):
        self.__phone = phone if phone is not None else ''
    
    @property
    def phone2(self):
        return self.__phone2

    @phone2.setter
    def phone2(self, phone2):
        self.__phone2 = phone2 if phone2 is not None else ''
    
    @property
    def mobile(self):
        return self.__mobile

    @mobile.setter
    def mobile(self, mobile):
        self.__mobile = mobile if mobile is not None else ''

    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, email):
        self.__email = email if email is not None else ''

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, title):
        self.__title = title if title is not None else ''

    @property
    def location(self):
        return self.__location

    @location.setter
    def location(self, location):
        self.__location = location if location is not None else ''

    @property
    def registration_number(self):
        return self.__registration_number

    @registration_number.setter
    def registration_number(self, registration_number):
        self.__registration_number = registration_number if registration_number is not None else ''

    @property
    def region_name(self):
        return self.__region_name

    @region_name.setter
    def region_name(self, region_name):
        self.__region_name = region_name if region_name is not None else ''

    @property
    def region_code(self):
        return self.__region_code

    @region_code.setter
    def region_code(self, region_code):
        self.__region_code = region_code if region_code is not None else ''

    @property
    def cities(self):
        return self.__cities

    @cities.setter
    def cities(self, cities):
        self.__cities = cities if cities is not None else ''
    
    def get_user_groups_ids(self):
        return [x.group_id for x in self.user_groups]

    def __str__(self):
        return f'ID: {self.id} LAST MODIFICATION DATE: {self.date_mod} ACTIVE: {self.active} NAME: {self.name} ' + \
                f'REALNAME: {self.realname} FIRSTNAME: {self.firstname} PHONE: {self.phone} PHONE2: {self.phone2} ' + \
                f'MOBILE: {self.mobile} EMAIL: {self.email} TITLE: {self.title} LOCATION: {self.location} ' + \
                f'REGISTRATION_NUMBER: {self.registration_number} CREATE USER: {self.create_user} ' + \
                f'USER GROUPS: {self.user_groups} SYNC COMMENT DATA: {self.sync_comment_data}' + \
                f'REGION NAME: {self.region_name} REGION CODE: {self.region_code} CITIES: {self.cities}' + \
                f'SHORT CELL PHONE NUMBER: {self.short_cell_phone_number}'


class GlpiGroupUserInfo:

    def __init__(self, relation_id, group_id, role):
        self.relation_id = relation_id
        self.group_id = group_id
        self.role = role

    @property
    def relation_id(self):
        return self.__relation_id

    @relation_id.setter
    def relation_id(self, relation_id):
        if relation_id is not None:
            self.__relation_id = relation_id
        else:
            raise ValueError('Relation ID can\'t be None.')

    @property
    def group_id(self):
        return self.__group_id

    @group_id.setter
    def group_id(self, group_id):
        if group_id is not None:
            self.__group_id = group_id
        else:
            raise ValueError('Group ID can\'t be None.')

    @property
    def role(self):
        return self.__role

    @role.setter
    def role(self, role):
        if role is not None:
            self.__role = role
        else:
            raise ValueError('Role can\'t be None.')

    def __str__(self):
        return f'RELATION_ID: {self.relation_id} GROUP ID: {self.group_id} ROLE: '\
            f'{DepartmentMember.get_role_representation(self.role)}'

    def __repr__(self):
        return f'RELATION_ID: {self.relation_id} GROUP ID: {self.group_id} ROLE: '\
            f'{DepartmentMember.get_role_representation(self.role)}'


class GlpiApi(ApiIntegrationService):

    def __init__(self, root_url, authorization, app_token, user_account_sync_group_name,
                user_data_sync_group_name, user_data_sync_from_comment_group_name,
                comment_data_start_separator, comment_data_end_separator, region_name_api_key,
                region_code_api_key, cities_api_key, short_cell_phone_number_api_key,
                parent_groups_names_to_sync=[], encoding='utf-8', content_type='application/json',
                init_run=True, timeout=30.03):
        super().__init__(root_url, encoding, timeout)

        self.content_type = content_type
        self.authorization = authorization
        self.app_token = app_token
        self.session_token = None

        self.parent_groups_names_to_sync = parent_groups_names_to_sync
        self.user_account_sync_group_id = None
        self.user_data_sync_group_id = None
        self.user_data_sync_from_comment_group_id = None

        self.comment_data_start_separator = comment_data_start_separator
        self.comment_data_end_separator = comment_data_end_separator
        self.region_name_api_key = region_name_api_key
        self.region_code_api_key = region_code_api_key
        self.cities_api_key = cities_api_key
        self.short_cell_phone_number_api_key = short_cell_phone_number_api_key

        self.glpi_groups = []
        self.glpi_users = []

        if init_run:
            self.run(user_account_sync_group_name, user_data_sync_group_name,
                    user_data_sync_from_comment_group_name)

    def run(self, user_account_sync_group_name, user_data_sync_group_name,
                                    user_data_sync_from_comment_group_name):
        self.init_session()

        self.fill_user_sync_groups_ids(user_account_sync_group_name, user_data_sync_group_name,
                                        user_data_sync_from_comment_group_name)
        self.fill_glpi_groups()
        self.fill_glpi_users()

        self.kill_session()

    def init_session(self):
        header = {
            'Content-Type': self.content_type,
            'Authorization': self.authorization,
            'App-Token': self.app_token,
        }

        response = self.get_response(self.get_init_session_url(), header)
        self.session_token = json.loads(response.text)['session_token']

    def get_init_session_url(self):
        return self.root_url + '/initSession/'
    
    def kill_session(self):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }

        response = self.get_response(self.get_kill_session_url(), header)
        self.session_token = None

    def get_kill_session_url(self):
        return self.root_url + '/killSession/'

    def fill_user_sync_groups_ids(self, user_account_sync_group_name, user_data_sync_group_name,
                                                        user_data_sync_from_comment_group_name):
        groups_data = self.groups()

        self.user_account_sync_group_id = self.get_group_id(user_account_sync_group_name, groups_data)
        self.user_data_sync_group_id = self.get_group_id(user_data_sync_group_name, groups_data)
        self.user_data_sync_from_comment_group_id = self.get_group_id(user_data_sync_from_comment_group_name,
                                                                                                groups_data)

        if not self.user_account_sync_group_id:
            general_functions.log_job_error(logger, glpi_integration_jobs.get_company_structure_sync_job_id(),
                f'User account sync group id is invalid: {self.user_account_sync_group_id}')

        if not self.user_data_sync_group_id:
            general_functions.log_job_error(logger, glpi_integration_jobs.get_company_structure_sync_job_id(), 
                f'User data sync group id is invalid: {self.user_data_sync_group_id}')

        if not self.user_data_sync_from_comment_group_id:
            general_functions.log_job_error(logger, glpi_integration_jobs.get_company_structure_sync_job_id(), 
                f'User data sync from comment group id is invalid: {self.user_data_sync_from_comment_group_id}')

    def get_group_id(self, group_name, groups_data):
        for group_data in groups_data:
            if group_data['name'] == group_name:
                return group_data['id']
        
        return None

    def fill_glpi_groups(self):
        groups_data = self.groups()
        parent_groups_ids_to_sync = self.get_parent_groups_ids_to_sync(groups_data)

        for group_data in groups_data:
            glpi_group = GlpiGroup(
                id=group_data['id'],
                name=group_data['name'],
                date_mod=group_data['date_mod'],
                level=group_data['level'],
                parent_groups_ids=[int(x) for x in json.loads(group_data['ancestors_cache'])]
            )

            if glpi_group.id in parent_groups_ids_to_sync:
                self.glpi_groups.append(glpi_group)
            else:
                if self.parent_group_allowed_to_sync(glpi_group.parent_groups_ids, parent_groups_ids_to_sync):
                    self.glpi_groups.append(glpi_group)
        
        if len(self.glpi_groups) > 1:
            self.glpi_groups.sort(key=lambda glpi_group: glpi_group.level)

    def groups(self):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'),)

        return self.get_response_data(self.get_groups_url(), header, params)

    def get_groups_url(self):
        return self.root_url + '/Group/'

    def get_parent_groups_ids_to_sync(self, groups_data):
        parent_groups_ids_to_sync = []

        for group_data in groups_data:
            group_id = group_data['id']
            group_name = group_data['name']

            if group_name in self.parent_groups_names_to_sync:
                parent_groups_ids_to_sync.append(group_id)
        
        return parent_groups_ids_to_sync

    def parent_group_allowed_to_sync(self, parent_group_ids, parent_groups_ids_to_sync):
        for parent_group_id in parent_group_ids:
            if parent_group_id in parent_groups_ids_to_sync:
                return True
        
        return False

    def fill_glpi_users(self):
        users_data = self.users()

        for user_data in users_data:
            user_groups_data = self.get_user_groups(user_data['id'])
            user_groups = []

            for user_group_data in user_groups_data:
                glpi_group_user_info = self.get_group_user_info(user_group_data)
                user_groups.append(glpi_group_user_info)

            if self.user_data_sync_group_id in [x.group_id for x in user_groups]:
                create_user = False
                
                if self.user_account_sync_group_id in [x.group_id for x in user_groups]:
                    create_user = True

                glpi_user = self.get_glpi_user(user_data, create_user, user_groups)
                self.glpi_users.append(glpi_user)      

    def users(self):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'), )
        
        return self.get_response_data(self.get_users_url(), header, params)
    
    def get_users_url(self):
        return self.root_url + '/User/'
    
    def get_user_groups(self, user_id):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'), )

        return self.get_response_data(self.get_user_groups_url(user_id), headers=header, params=params)

    def get_user_groups_url(self, user_id):
        return self.root_url + f'/User/{user_id}/Group_user/'

    def get_group_user_info(self, user_group_data):
        role = DepartmentMember.MEMBER_ROLE

        if user_group_data['is_userdelegate']:
            role = DepartmentMember.DEPUTY_MANAGER_ROLE

        if user_group_data['is_manager']:
            role = DepartmentMember.MANAGER_ROLE
        
        return GlpiGroupUserInfo(user_group_data['id'], user_group_data['groups_id'], role)

    def get_glpi_user(self, user_data, create_user, user_groups):
        user_email = None

        for user_email_data in self.get_user_email_data(user_data['id']):
            if user_email_data['is_default']:
                user_email = user_email_data['email']

        user_title_data = self.get_user_title_data(user_data['id'])
        user_title = user_title_data[0]['name'] if len(user_title_data) == 1 else None
        user_location_data = self.get_user_location_data(user_data['id'])
        user_location = user_location_data[0]['completename'] if len(user_location_data) == 1 else None
        user_is_active = self.determine_user_active(user_data)

        glpi_user = GlpiUser(
            user_data['id'], user_data['date_mod'], user_is_active, user_data['name'], 
            user_data['realname'], user_data['firstname'], user_data['phone'], user_data['phone2'],
            user_data['mobile'], user_email, user_title, user_location, user_data['registration_number'],
            create_user
        )

        if self.user_data_sync_from_comment_group_id in [x.group_id for x in user_groups]:
            glpi_user.sync_comment_data = True
            comment_data = self.extract_comment_data(user_data['comment'])

            if comment_data:
                self.fill_user_with_comment_data(glpi_user, comment_data)
            else:
                general_functions.log_job_error(logger, glpi_integration_jobs.get_company_structure_sync_job_id(), 
                    _('Comment data for user %(username)s could not be extracted.') % {'username': user_data['name']})

        sync_groups_ids = (
            self.user_account_sync_group_id,
            self.user_data_sync_group_id,
            self.user_data_sync_from_comment_group_id
        )
        glpi_user.user_groups = [x for x in user_groups if x.group_id not in sync_groups_ids]

        return glpi_user

    def get_user_email_data(self, user_id):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'), )

        return self.get_response_data(self.get_user_email_data_url(user_id), headers=header, params=params)

    def get_user_email_data_url(self, user_id):
        return self.root_url + f'/User/{user_id}/useremail/'

    def get_user_title_data(self, user_id):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'), )

        return self.get_response_data(self.get_user_title_data_url(user_id), headers=header, params=params)

    def get_user_title_data_url(self, user_id):
        return self.root_url + f'/User/{user_id}/usertitle/'

    def get_user_location_data(self, user_id):
        header = {
            'Content-Type': self.content_type,
            'Session-Token': self.session_token,
            'App-Token': self.app_token,
        }
        params = (('get_hateoas', 'false'), )

        return self.get_response_data(self.get_user_location_data_url(user_id), headers=header, params=params)

    def get_user_location_data_url(self, user_id):
        return self.root_url + f'/User/{user_id}/location/'

    def extract_comment_data(self, comment):
        try:
            start_index = comment.find(self.comment_data_start_separator) + len(self.comment_data_start_separator)
            end_index = comment.rfind(self.comment_data_end_separator)
            comment_data = json.loads(comment[start_index:end_index])
        except Exception as e:
            general_functions.log_job_exception(logger, glpi_integration_jobs.get_company_structure_sync_job_id(), 
                _('Exception occured while extracting data from comment: %(e)s') % {'e': str(e)})
            return None
        else:
            return comment_data

    def fill_user_with_comment_data(self, glpi_user, comment_data):
        if self.region_name_api_key in comment_data:
            glpi_user.sync_region_name = True
            glpi_user.region_name = comment_data[self.region_name_api_key]

        if self.region_code_api_key in comment_data:
            glpi_user.sync_region_code = True
            glpi_user.region_code = comment_data[self.region_code_api_key]

        if self.cities_api_key in comment_data:
            glpi_user.sync_cities = True
            glpi_user.cities = comment_data[self.cities_api_key]

        if self.short_cell_phone_number_api_key in comment_data:
            glpi_user.sync_short_cell_phone_number = True
            glpi_user.short_cell_phone_number = comment_data[self.short_cell_phone_number_api_key]

    def determine_user_active(self, user_data):
        active = user_data['is_active']

        if user_data['begin_date'] and len(user_data['begin_date']) > 3:
            begin_date = general_functions.validated_datetime_else_none(user_data['begin_date'][:-3])
        else:
            begin_date = None

        if user_data['end_date'] and len(user_data['end_date']) > 3:
            end_date = general_functions.validated_datetime_else_none(user_data['end_date'][:-3])
        else:
            end_date = None

        now = timezone.localtime(timezone.now())
        now = datetime(year=now.year, month=now.month, day=now.day, hour=now.hour,
                        minute=now.minute, second=now.second)

        if begin_date:
            if begin_date >= now:
                return False

        if end_date:
            if end_date <= now:
                return False

        return active
