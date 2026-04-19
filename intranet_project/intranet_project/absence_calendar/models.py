from datetime import date

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.utils.translation import pgettext

from company_structure.models import Employee
from intranet_project import general_functions
from live_settings.global_live_settings import global_live_settings


class Event(models.Model):
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')

    title = models.CharField(max_length=50, verbose_name=pgettext('title', 'the name of something'))
    date = models.DateField(verbose_name=_('date'))
    description = models.TextField(null=False, blank=True, verbose_name=_('description'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('created by'))

    def __str__(self):
        return self.title


class AbsenceType(models.Model):
    class Meta:
        verbose_name = _('absence type')
        verbose_name_plural = _('absence types')

    text = models.TextField(verbose_name=_('text'))
    visible = models.BooleanField(default=True, verbose_name=_('visible'))
    default = models.BooleanField(default=False, verbose_name=_('default'))

    def __str__(self):
        return self.text

    def clean(self):
        self.validate_default()

    def validate_default(self):
        if self.default and self.visible:
            default_absence_type = AbsenceType.get_default_absence_type_or_none()

            if default_absence_type and self != default_absence_type:
                raise ValidationError(
                    _('There can be only one visible default absence type \
                        (current default: %(current_default)s).'),
                    code='maximum_number_of_default_visible_absence_types_exceeded',
                    params={'current_default': default_absence_type}
                )
    
    @staticmethod
    def get_default_absence_type_or_none():
        return general_functions.get_object_or_none(AbsenceType, default=True, visible=True)


class Absence(models.Model):
    class Meta:
        verbose_name = _('absence')
        verbose_name_plural = _('absences')
        
    absent = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('absent'))
    absence_type =  models.ForeignKey(AbsenceType, on_delete=models.PROTECT, null=False,
                                        limit_choices_to={'visible': True}, verbose_name=_('absence type'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    additional_information = models.TextField(null=False, blank=True, verbose_name=_('additional information'))

    def clean(self):
        validate_start_earlier_than_or_equal_end_date(self.start_date, self.end_date)

    @staticmethod
    def validate_user_absence_one_at_a_time(user, start_date, end_date, absence_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date, absence_id) + \
                                    get_colliding_vacation_leaves_str(user, start_date, end_date) + \
                                    get_colliding_special_leaves_str(user, start_date, end_date)  + \
                                    get_colliding_remote_works_str(user, start_date, end_date)

        handle_colliding_absences_str(colliding_absences_str)

    def can_update(self):
        return general_functions.current_date() <= self.start_date

    def can_finish_earlier(self):
        today = general_functions.current_date()
        return today > self.start_date and today < self.end_date

    def can_delete(self):
        return True

    def name(self):
        return self.absence_type.text

    def __str__(self):
        return f'{self.absent} | {self.start_date} - {self.end_date}'

    @staticmethod
    def fill_query_args_end_date__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'end_date__gte', date)

    @staticmethod
    def fill_query_args_start_date__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'start_date__lte', date)
    
    @staticmethod
    def fill_query_args_absence_type(kwargs, value):
        try:
            absence_type = int(value)
        except ValueError:
            pass
        else:
            kwargs['absence_type'] = absence_type


#######################################################################
# VacationLeave
#######################################################################


class VacationLeaveType(models.Model):
    class Meta:
        verbose_name = _('vacation leave type')
        verbose_name_plural = _('vacation leave types')

    text = models.TextField(verbose_name=_('text'))
    max_number_of_days = models.PositiveIntegerField(verbose_name=_('max number of days'))
    visible = models.BooleanField(default=True, verbose_name=_('visible'))
    default = models.BooleanField(default=False, verbose_name=_('default'))

    def clean(self):
        self.validate_default()

    def validate_default(self):
        if self.default and self.visible:
            default_vacation_leave_type = VacationLeaveType.get_default_vacation_leave_type_or_none()

            if default_vacation_leave_type and self != default_vacation_leave_type:
                raise ValidationError(
                    _('There can be only one visible default vacation leave type \
                        (current default: %(current_default)s).'),
                    code='maximum_number_of_default_visible_vacation_leave_types_exceeded',
                    params={'current_default': default_vacation_leave_type}
                )

    @staticmethod
    def get_default_vacation_leave_type_or_none():
        return general_functions.get_object_or_none(VacationLeaveType, default=True, visible=True)

    def __str__(self):
        return self.text


class VacationLeaveDocument(models.Model):
    class Meta:
        verbose_name = _('vacation leave document')
        verbose_name_plural = _('vacation leave documents')

    document_id = models.PositiveIntegerField(verbose_name=_('document ID'))
    absent_name = models.CharField(max_length=250, verbose_name=_('absent name'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    leave_for_year = models.PositiveIntegerField(verbose_name=_('leave for year'))
    number_of_days = models.PositiveIntegerField(verbose_name=_('number of days'))
    vacation_leave_type = models.TextField(verbose_name=_('vacation leave type'))
    decisive_name = models.CharField(max_length=250, verbose_name=_('decisive name'))
    date_of_completion = models.DateField(verbose_name=_('date of completion'))
    registration_number = models.CharField(max_length=20, verbose_name=_('registration number'))
    department_name = models.CharField(max_length=250, null=True, blank=True,
                                        verbose_name=_('department name'))
    department_manager_name = models.CharField(max_length=250, null=True, blank=True,
                                                verbose_name=_('department manager name'))
    city = models.CharField(max_length=50, verbose_name=_('city'))

    def __str__(self):
        return f'{_("Document")} {self.absent_name} - {self.start_date}-{self.end_date}'


class VacationLeave(models.Model):
    class Meta:
        verbose_name = _('vacation leave')
        verbose_name_plural = _('vacation leaves')
        permissions = (
            ('moderate_vacation_leave', 'Can moderate vacation leaves'),
            ('view_vacation_leave_document', 'Can view vacation leave document'),
        )

    PENDING_STATUS = 1
    ACCEPTED_STATUS = 2
    REJECTED_STATUS = 3
    CANCELED_STATUS = 4
    CANCELED_BY_DECISIVE_STATUS = 5
    PENDING_TO_CANCEL_STATUS = 6
    PENDING_TO_FINISH_EARLIER_STATUS = 7

    STATUS_CHOICES = (
        (PENDING_STATUS, _('Pending')),
        (ACCEPTED_STATUS, _('Accepted')),
        (REJECTED_STATUS, _('Rejected')),
        (CANCELED_STATUS, _('Canceled')),
        (CANCELED_BY_DECISIVE_STATUS, _('Canceled by decisive person')),
        (PENDING_TO_CANCEL_STATUS, _('Pending to cancel')),
        (PENDING_TO_FINISH_EARLIER_STATUS, _('Pending to finish earlier')),
    )

    absent = models.ForeignKey(User, related_name='VLEmployee', on_delete=models.PROTECT, verbose_name=_('absent'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    leave_for_year = models.PositiveIntegerField(default=2020, verbose_name=_('leave for year'),
                            validators=[MinValueValidator(2019), MaxValueValidator(9999)])
    number_of_days = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                                verbose_name=_('number of days'))
    vacation_leave_type = models.ForeignKey(VacationLeaveType, on_delete=models.PROTECT, null=False,
                                            limit_choices_to={'visible': True}, verbose_name=_('vacation leave type'))

    decisive_person = models.ForeignKey(User, related_name='VLDecisive', default=None, 
                                        on_delete=models.PROTECT, null=True, verbose_name=_('decisive person'))
    message_for_decisive_person = models.TextField(null=False, blank=True, verbose_name=_('message for decisive person'))
    date_of_completion = models.DateField(default=timezone.now, verbose_name=_('date of completion'))
    
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS, verbose_name=_('status'))
    status_changed_by = models.ForeignKey(User, related_name='VLSupervisor', default=None, 
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('status changed by'))
    last_status_change_time = models.DateTimeField(default=None, null=True, blank=True, 
                                                    verbose_name=_('last status change time'))
    rejection_reason = models.TextField(null=False, blank=True, verbose_name=_('rejection reason'))

    pending_end_date = models.DateField(null=True, blank=True, verbose_name=_('pending end date'))
    pending_number_of_days = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)],
                                            verbose_name=_('pending number of days'))

    document = models.OneToOneField(VacationLeaveDocument, on_delete=models.SET_NULL, default=None,
                                    null=True, blank=True, related_name='vacation_leave', verbose_name=_('document'))

    def clean(self):
        validate_start_earlier_than_or_equal_end_date(self.start_date, self.end_date)
        validate_start_later_than_or_equal_date_of_completion(self.start_date, self.date_of_completion)
        self.validate_number_of_days_for_vacation_leave_type()
        self.validate_decisive_person()

    def validate_number_of_days_for_vacation_leave_type(self):
        if self.number_of_days > self.vacation_leave_type.max_number_of_days:
            raise ValidationError(
                _('The maximum number of leave days for this vacation leave type is %(max_number_of_days)s.'),
                code='maximum_number_of_leave_days_exceeded',
                params={'max_number_of_days': self.vacation_leave_type.max_number_of_days}
            )
    
    def validate_decisive_person(self):
        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            raise ValidationError(
                _('You need to have employee assigned in order to plan vacation leave.'),
                code='employee_not_assigned'
            )
        else:
            supervisors_ids = employee.get_supervisor_users_ids()

            if self.decisive_person.id not in supervisors_ids:
                raise ValidationError(
                    _('You chose wrong decisive person.'),
                    code='wrong_decisive_person',
                )

    @staticmethod
    def validate_user_vacation_leave_one_at_a_time(user, start_date, end_date, vacation_leave_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date, vacation_leave_id) + \
                    get_colliding_special_leaves_str(user, start_date, end_date) + \
                    get_colliding_remote_works_str(user, start_date, end_date)

        handle_colliding_absences_str(colliding_absences_str)

    @staticmethod
    def get_colliding_absences_info(user, start_date, end_date, vacation_leave_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date, vacation_leave_id) + \
                    get_colliding_special_leaves_str(user, start_date, end_date) + \
                    get_colliding_remote_works_str(user, start_date, end_date)

        return colliding_absences_str

    @staticmethod
    def validate_pending_number_of_days(start_date, pending_end_date, pending_number_of_days):
        number_of_days_in_date_range = (pending_end_date - start_date).days + 1

        if number_of_days_in_date_range < pending_number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )

    @staticmethod
    def validate_number_of_days(start_date, end_date, number_of_days):
        number_of_days_in_date_range = (end_date - start_date).days + 1

        if number_of_days_in_date_range < number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )

    def can_update(self):
        return general_functions.current_date() <= self.start_date and self.is_pending()

    def can_finish_earlier(self):
        today = general_functions.current_date()
        return today > self.start_date and today <= self.end_date and self.is_accepted()

    def can_cancel(self):
        if not self.is_accepted():
            return False
        
        return general_functions.current_date() <= self.start_date

    def can_delete(self):
        return self.is_pending()

    def can_change_decision(self):
        if not self.is_accepted() and not self.is_rejected():
            return False
        
        return general_functions.current_date() < self.start_date

    def is_pending(self):
        return self.status == VacationLeave.PENDING_STATUS

    def is_accepted(self):
        return self.status == VacationLeave.ACCEPTED_STATUS

    def is_rejected(self):
        return self.status == VacationLeave.REJECTED_STATUS \
            or self.status == VacationLeave.CANCELED_BY_DECISIVE_STATUS

    def is_canceled(self):
        return self.status == VacationLeave.CANCELED_STATUS

    def is_finished(self):
        today = general_functions.current_date()
        return today > self.end_date and self.is_accepted()

    def is_pending_to_cancel(self):
        return self.status == VacationLeave.PENDING_TO_CANCEL_STATUS
    
    def is_pending_to_finish_earlier(self):
        return self.status == VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS

    def create_document(self):
        with transaction.atomic():
            document = VacationLeaveDocument(
                start_date=self.start_date,
                end_date=self.end_date,
                leave_for_year=self.leave_for_year,
                number_of_days=self.number_of_days,
                vacation_leave_type=self.vacation_leave_type.text,
                date_of_completion=self.date_of_completion,
                document_id=self.id,
                absent_name=self.absent.profile.get_name(),
                decisive_name=self.decisive_person.profile.get_name(),
                registration_number=self.absent.employee.registration_number,
                department_name=self.absent.employee.get_department_name(),
                department_manager_name=self.absent.employee.get_department_manager_name(),
                city=global_live_settings.company.city,
            )
            
            try:
                document.full_clean()
            except ValidationError as e:
                raise e
            else:
                document.vacation_leave = self
                document.save()

                self.document = document
                self.save()

    def save(self, *args, **kwargs):
        if self.is_pending() or self.is_pending_to_cancel() or self.is_pending_to_finish_earlier():
            self.rejection_reason = ''

        if self.is_pending():
            self.status_changed_by = None
            self.last_status_change_time = None

        super(VacationLeave, self).save(*args, **kwargs)

    def name(self):
        return f'{_("Vacation leave")}'

    def __str__(self):
        return f'{self.absent} - {self.start_date}-{self.end_date}'

    @staticmethod
    def get_number_of_vacation_leaves_to_moderate(decisive_person):
        return VacationLeave.objects.filter(status__in=(
                                                VacationLeave.PENDING_STATUS,
                                                VacationLeave.PENDING_TO_CANCEL_STATUS,
                                                VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS,
                                            ),
                                            decisive_person=decisive_person).count()

    @staticmethod
    def get_status_representation(status):
        for status_choice in VacationLeave.STATUS_CHOICES:
            if status_choice[0] == status:
                return status_choice[1]

        raise ValueError('Wrong vacation leave status was given.')
    
    @staticmethod
    def get_statuses():
        return {
            'PENDING': {
                'value': VacationLeave.PENDING_STATUS,
                'representation': VacationLeave.get_status_representation(VacationLeave.PENDING_STATUS),
            },
            'ACCEPTED': {
                'value': VacationLeave.ACCEPTED_STATUS,
                'representation': VacationLeave.get_status_representation(VacationLeave.ACCEPTED_STATUS),
            },
            'REJECTED': {
                'value': VacationLeave.REJECTED_STATUS,
                'representation': VacationLeave.get_status_representation(VacationLeave.REJECTED_STATUS),
            },
            'CANCELED': {
                'value': VacationLeave.CANCELED_STATUS,
                'representation': VacationLeave.get_status_representation(VacationLeave.CANCELED_STATUS),
            },
            'CANCELED_BY_DECISIVE': {
                'value': VacationLeave.CANCELED_BY_DECISIVE_STATUS,
                'representation': VacationLeave.get_status_representation(
                        VacationLeave.CANCELED_BY_DECISIVE_STATUS
                    ),
            },
            'PENDING_TO_CANCEL': {
                'value': VacationLeave.PENDING_TO_CANCEL_STATUS,
                'representation': VacationLeave.get_status_representation(
                        VacationLeave.PENDING_TO_CANCEL_STATUS
                    ),
            },
            'PENDING_TO_FINISH_EARLIER': {
                'value': VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS,
                'representation': VacationLeave.get_status_representation(
                        VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS
                    ),
            },
        }

    @staticmethod
    def fill_query_args_absent_first_last_name(kwargs, first_name, last_name):
        kwargs['absent__in'] = []
        absent_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if absent_users:
            kwargs['absent__in'] = absent_users
    
    @staticmethod
    def fill_query_args_decisive_first_last_name(kwargs, first_name, last_name):
        kwargs['decisive_person__in'] = []
        decisive_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if decisive_users:
            kwargs['decisive_person__in'] = decisive_users

    @staticmethod
    def fill_query_args_end_date__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'end_date__gte', date)

    @staticmethod
    def fill_query_args_start_date__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'start_date__lte', date)

    @staticmethod
    def fill_query_args_date_of_completion__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__gte', date)

    @staticmethod
    def fill_query_args_date_of_completion__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__lte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__gte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__gte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__lte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__lte', date)

    @staticmethod
    def fill_query_args_leave_for_year(kwargs, value):
        try:
            kwargs['leave_for_year'] = int(value)
        except ValueError:
            pass

    @staticmethod

    def fill_query_args_vacation_leave_type(kwargs, value):
        try:
            vacation_leave_type_id = int(value)
        except ValueError:
            pass
        else:
            kwargs['vacation_leave_type'] = vacation_leave_type_id
    
    @staticmethod
    def fill_query_args_status(kwargs, value):
        try:
            leave_status = int(value)
        except ValueError:
            pass
        else:
            kwargs['status'] = leave_status

    @staticmethod
    def fill_query_args_status_one_of(args, kwargs, value, statuses):
        try:
            leave_status = int(value)
        except ValueError:
            args.append(VacationLeave.get_statuses_args(statuses))
        else:
            if leave_status in statuses:
                kwargs['status'] = leave_status
            else:
                args.append(VacationLeave.get_statuses_args(statuses))

    @staticmethod
    def get_statuses_args(statuses):
        query = Q(status=statuses[0])

        for status in statuses[1:]:
            query |= Q(status=status)

        return query
    
    @staticmethod
    def fill_query_args_vacation_leave_id(kwargs, value):
        try:
            kwargs['id'] = int(value)
        except ValueError:
            pass


#######################################################################
# SpecialLeave
#######################################################################


class SpecialLeaveReason(models.Model):
    class Meta:
        verbose_name = _('special leave reason')
        verbose_name_plural = _('special leave reasons')
    
    text = models.TextField(verbose_name=_('text'))
    text_in_application = models.TextField(verbose_name=_('text in application'))
    max_number_of_days = models.PositiveIntegerField(verbose_name=_('max number of days'))
    visible = models.BooleanField(default=True, verbose_name=_('visible'))

    def __str__(self):
        return self.text


class SpecialLeaveConfirmationDocumentName(models.Model):
    class Meta:
        verbose_name = _('special leave confirmation document name')
        verbose_name_plural = _('special leave confirmation document names')

    text = models.TextField(verbose_name=_('text'))
    text_in_application = models.TextField(verbose_name=_('text in application'))
    visible = models.BooleanField(default=True, verbose_name=_('visible'))

    def __str__(self):
        return self.text


class SpecialLeaveDocument(models.Model):
    class Meta:
        verbose_name = _('special leave document')
        verbose_name_plural = _('special leave documents')

    document_id = models.PositiveIntegerField(verbose_name=_('document ID'))
    absent_name = models.CharField(max_length=250, verbose_name=_('absent name'))
    registration_number = models.CharField(max_length=20, verbose_name=_('registration number'))
    city = models.CharField(max_length=50, verbose_name=_('city'))
    date_of_completion = models.DateField(verbose_name=_('date of completion'))
    company_name = models.CharField(max_length=100, verbose_name=_('company name'))
    number_of_days = models.PositiveIntegerField(verbose_name=_('number of days'))
    reason = models.TextField(verbose_name=_('reason'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    decisive_name = models.CharField(max_length=250, verbose_name=_('decisive name'))
    confirmation_document_name = models.TextField(verbose_name=_('confirmation document name'))
    confirmation_document_number = models.CharField(max_length=30, verbose_name=_('confirmation document number'))
    confirmation_document_issue_date = models.DateField(verbose_name=_('confirmation document issue date'))
    confirming_person_name = models.CharField(max_length=250, verbose_name=_('confirming person name'))

    def __str__(self):
        return f'{_("Document")} {self.absent_name} - {self.start_date}-{self.end_date}'


class SpecialLeave(models.Model):

    class Meta:
        verbose_name = _('special leave')
        verbose_name_plural = _('special leaves')
        permissions = (
            ('moderate_special_leave', 'Can moderate special leaves'), 
            ('view_special_leave_document', 'Can view special leave document'),
        )

    PENDING_STATUS = 1
    ACCEPTED_STATUS = 2
    REJECTED_STATUS = 3
    CANCELED_STATUS = 4
    CANCELED_BY_DECISIVE_STATUS = 5
    CONFIRMED_STATUS = 6
    PENDING_TO_CANCEL_STATUS = 7
    PENDING_TO_FINISH_EARLIER_STATUS = 8

    STATUS_CHOICES = (
        (PENDING_STATUS, _('Pending')),
        (ACCEPTED_STATUS, _('Accepted')),
        (REJECTED_STATUS, _('Rejected')),
        (CANCELED_STATUS, _('Canceled')),
        (CANCELED_BY_DECISIVE_STATUS, _('Canceled by decisive person')),
        (CONFIRMED_STATUS, _('Confirmed')),
        (PENDING_TO_CANCEL_STATUS, _('Pending to cancel')),
        (PENDING_TO_FINISH_EARLIER_STATUS, _('Pending to finish earlier')),
    )

    absent = models.ForeignKey(User, related_name='SLEmployee', on_delete=models.PROTECT,
                                verbose_name=_('absent'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    reason = models.ForeignKey(SpecialLeaveReason, on_delete=models.PROTECT, null=True, 
                                                    limit_choices_to={'visible': True}, verbose_name=_('reason'))
    number_of_days = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                                verbose_name=_('number of days'))
    date_of_completion = models.DateField(default=timezone.now, verbose_name=_('date of completion'))
    decisive_person = models.ForeignKey(User, related_name='SLDecisive', default=None, 
                                        on_delete=models.PROTECT, null=True, verbose_name=_('decisive person'))
    
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS, verbose_name=_('status'))
    status_changed_by = models.ForeignKey(User, related_name='SLSupervisor', default=None,
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('status changed by'))
    last_status_change_time = models.DateTimeField(default=None, null=True, blank=True,
                                                    verbose_name=_('last status change time'))
    message_for_decisive_person = models.TextField(null=False, blank=True,
                                                    verbose_name=_('message for decisive person'))
    rejection_reason = models.TextField(null=False, blank=True, verbose_name=_('rejection reason'))

    pending_end_date = models.DateField(null=True, blank=True, verbose_name=_('pending end date'))
    pending_number_of_days = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)],
                                            verbose_name=_('pending number of days'))

    confirmation_document_name = models.ForeignKey(SpecialLeaveConfirmationDocumentName, 
            on_delete=models.PROTECT, default=None, null=True, blank=True, limit_choices_to={'visible': True},
            verbose_name=_('confirmation document name'))
    confirmation_document_number = models.CharField(max_length=30, default=None, null=True, blank=True,
                                                    verbose_name=_('confirmation document number'))
    confirmation_document_issue_date = models.DateField(default=None, null=True, blank=True,
                                                        verbose_name=_('confirmation document issue date'))
    confirming_person = models.ForeignKey(User, related_name='SLConfirming', default=None,
                                            on_delete=models.PROTECT, null=True, blank=True,
                                            verbose_name=_('confirming person'))
    document = models.OneToOneField(SpecialLeaveDocument, on_delete=models.SET_NULL, default=None,
                                    null=True, blank=True, related_name='special_leave',
                                    verbose_name=_('document'))

    def clean(self):
        validate_start_earlier_than_or_equal_end_date(self.start_date, self.end_date)
        validate_start_later_than_or_equal_date_of_completion(self.start_date, self.date_of_completion)
        self.validate_number_of_days_for_reason()
        self.validate_decisive_person()

    def validate_number_of_days_for_reason(self):
        if self.number_of_days > self.reason.max_number_of_days:
            raise ValidationError(_('The maximum number of leave days for this reason is %(max_number_of_days)s.'),
                            code='maximum_number_of_leave_days_exceeded',
                            params={'max_number_of_days': self.reason.max_number_of_days}
                        )

    def validate_decisive_person(self):
        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            raise ValidationError(
                _('You need to have employee assigned in order to plan special leave.'),
                code='employee_not_assigned'
            )
        else:
            supervisors_ids = employee.get_supervisor_users_ids()

            if self.decisive_person.id not in supervisors_ids:
                raise ValidationError(
                    _('You chose wrong decisive person.'),
                    code='wrong_decisive_person',
                )

    @staticmethod
    def validate_user_special_leave_one_at_a_time(user, start_date, end_date, special_leave_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date) + \
                    get_colliding_special_leaves_str(user, start_date, end_date, special_leave_id) + \
                    get_colliding_remote_works_str(user, start_date, end_date)

        handle_colliding_absences_str(colliding_absences_str)

    @staticmethod
    def get_colliding_absences_info(user, start_date, end_date, special_leave_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date) + \
                    get_colliding_special_leaves_str(user, start_date, end_date, special_leave_id) + \
                    get_colliding_remote_works_str(user, start_date, end_date)

        return colliding_absences_str

    @staticmethod
    def validate_pending_number_of_days(start_date, pending_end_date, pending_number_of_days):
        number_of_days_in_date_range = (pending_end_date - start_date).days + 1

        if number_of_days_in_date_range < pending_number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )

    @staticmethod
    def validate_number_of_days(start_date, end_date, number_of_days):
        number_of_days_in_date_range = (end_date - start_date).days + 1

        if number_of_days_in_date_range < number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )

    def can_update(self):
        return general_functions.current_date() <= self.start_date \
                        and self.status == SpecialLeave.PENDING_STATUS

    def can_finish_earlier(self):
        today = general_functions.current_date()
        return today > self.start_date and today <= self.end_date and (self.is_accepted() or self.is_confirmed())

    def can_cancel(self):
        if not self.is_accepted() and not self.is_confirmed():
            return False
        
        return general_functions.current_date() <= self.start_date

    def can_delete(self):
        return self.status == SpecialLeave.PENDING_STATUS

    def can_change_decision(self):
        if not self.is_accepted() and not self.is_confirmed() and not self.is_rejected():
            return False
        
        return general_functions.current_date() < self.start_date

    def can_update_document_confirmation_data(self):
        if self.is_accepted() or self.is_pending() or self.is_pending_to_cancel() or \
            self.is_pending_to_finish_earlier():
            return True
        
        return False

    def can_confirm_document_data(self):
        if self.is_confirmed():
            return False

        if self.is_accepted() or self.is_pending_to_cancel() or self.is_pending_to_finish_earlier():
            return self.confirmation_document_name and self.confirmation_document_number\
                and self.confirmation_document_issue_date

        return False

    def is_pending(self):
        return self.status == SpecialLeave.PENDING_STATUS

    def is_accepted(self):
        return self.status == SpecialLeave.ACCEPTED_STATUS

    def is_rejected(self):
        return self.status == SpecialLeave.REJECTED_STATUS \
            or self.status == SpecialLeave.CANCELED_BY_DECISIVE_STATUS

    def is_canceled(self):
        return self.status == SpecialLeave.CANCELED_STATUS

    def is_confirmed(self):
        return self.status == SpecialLeave.CONFIRMED_STATUS

    def is_finished(self):
        today = general_functions.current_date()
        return today > self.end_date and self.is_confirmed()

    def is_pending_to_cancel(self):
        return self.status == SpecialLeave.PENDING_TO_CANCEL_STATUS

    def is_pending_to_finish_earlier(self):
        return self.status == SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS

    def create_document(self):
        with transaction.atomic():
            document = SpecialLeaveDocument(
                start_date=self.start_date,
                end_date=self.end_date,
                document_id=self.id,
                absent_name=self.absent.profile.get_name(),
                number_of_days=self.number_of_days,
                decisive_name=self.decisive_person.profile.get_name(),
                date_of_completion=self.date_of_completion,
                registration_number=self.absent.employee.registration_number,
                city=global_live_settings.company.city,
                company_name=global_live_settings.company.name,
                reason=self.reason.text_in_application,
                confirmation_document_name=self.confirmation_document_name.text_in_application,
                confirmation_document_number=self.confirmation_document_number,
                confirmation_document_issue_date=self.confirmation_document_issue_date,
                confirming_person_name=self.confirming_person.profile.get_name(),
            )

            try:
                document.full_clean()
            except ValidationError as e:
                raise e
            else:
                document.special_leave = self
                document.save()

                self.document = document
                self.save()

    def save(self, *args, **kwargs):
        if self.is_pending() or self.is_pending_to_cancel() or self.is_pending_to_finish_earlier():
            self.rejection_reason = ''

        if self.is_pending():
            self.status_changed_by = None
            self.last_status_change_time = None

        super(SpecialLeave, self).save(*args, **kwargs)

    def name(self):
        return f'{_("Special leave")}'

    def __str__(self):
        return f'{self.absent} - {self.start_date}-{self.end_date}'

    @staticmethod
    def get_number_of_special_leaves_to_moderate(decisive_person):
        return SpecialLeave.objects.filter(status__in=(SpecialLeave.PENDING_STATUS,
                                            SpecialLeave.PENDING_TO_CANCEL_STATUS,
                                            SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS),
                                            decisive_person=decisive_person).count()
    
    @staticmethod
    def get_status_representation(status):
        for status_choice in SpecialLeave.STATUS_CHOICES:
            if status_choice[0] == status:
                return status_choice[1]

        raise ValueError('Wrong vacation leave status was given.')

    @staticmethod
    def get_statuses():
        return {
            'PENDING': {
                'value': SpecialLeave.PENDING_STATUS,
                'representation': SpecialLeave.get_status_representation(SpecialLeave.PENDING_STATUS),
            },
            'ACCEPTED': {
                'value': SpecialLeave.ACCEPTED_STATUS,
                'representation': SpecialLeave.get_status_representation(SpecialLeave.ACCEPTED_STATUS),
            },
            'REJECTED': {
                'value': SpecialLeave.REJECTED_STATUS,
                'representation': SpecialLeave.get_status_representation(SpecialLeave.REJECTED_STATUS),
            },
            'CANCELED': {
                'value': SpecialLeave.CANCELED_STATUS,
                'representation': SpecialLeave.get_status_representation(SpecialLeave.CANCELED_STATUS),
            },
            'CANCELED_BY_DECISIVE': {
                'value': SpecialLeave.CANCELED_BY_DECISIVE_STATUS,
                'representation': SpecialLeave.get_status_representation(
                        SpecialLeave.CANCELED_BY_DECISIVE_STATUS
                    ),
            },
            'CONFIRMED': {
                'value': SpecialLeave.CONFIRMED_STATUS,
                'representation': SpecialLeave.get_status_representation(SpecialLeave.CONFIRMED_STATUS),
            },
            'PENDING_TO_CANCEL': {
                'value': SpecialLeave.PENDING_TO_CANCEL_STATUS,
                'representation': SpecialLeave.get_status_representation(
                    SpecialLeave.PENDING_TO_CANCEL_STATUS
                    ),
            },
            'PENDING_TO_FINISH_EARLIER': {
                'value': SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS,
                'representation': SpecialLeave.get_status_representation(
                    SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS
                    ),
            },
        }

    @staticmethod
    def fill_query_args_absent_first_last_name(kwargs, first_name, last_name):
        kwargs['absent__in'] = []
        absent_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if absent_users:
            kwargs['absent__in'] = absent_users
    
    @staticmethod
    def fill_query_args_decisive_first_last_name(kwargs, first_name, last_name):
        kwargs['decisive_person__in'] = []
        decisive_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if decisive_users:
            kwargs['decisive_person__in'] = decisive_users

    @staticmethod
    def fill_query_args_end_date__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'end_date__gte', date)

    @staticmethod
    def fill_query_args_start_date__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'start_date__lte', date)

    @staticmethod
    def fill_query_args_date_of_completion__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__gte', date)

    @staticmethod
    def fill_query_args_date_of_completion__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__lte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__gte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__gte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__lte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__lte', date)

    @staticmethod
    def fill_query_args_status(kwargs, value):
        try:
            leave_status = int(value)
        except ValueError:
            pass
        else:
            kwargs['status'] = leave_status

    @staticmethod
    def fill_query_args_status_one_of(args, kwargs, value, statuses):
        try:
            leave_status = int(value)
        except ValueError:
            args.append(SpecialLeave.get_statuses_args(statuses))
        else:
            if leave_status in statuses:
                kwargs['status'] = leave_status
            else:
                args.append(SpecialLeave.get_statuses_args(statuses))

    @staticmethod
    def get_statuses_args(statuses):
        query = Q(status=statuses[0])

        for status in statuses[1:]:
            query |= Q(status=status)

        return query

    @staticmethod
    def fill_query_args_special_leave_reason(kwargs, value):
        try:
            special_leave_reason_id = int(value)
        except ValueError:
            pass
        else:
            kwargs['reason'] = special_leave_reason_id

    @staticmethod
    def fill_query_args_confirmative_first_last_name(kwargs, first_name, last_name):
        kwargs['confirming_person__in'] = []
        confirming_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if confirming_users:
            kwargs['confirming_person__in'] = confirming_users

    @staticmethod
    def fill_query_args_special_leave_id(kwargs, value):
        try:
            kwargs['id'] = int(value)
        except ValueError:
            pass

#######################################################################
# RemoteWork
#######################################################################

class RemoteWorkDocument(models.Model):
    class Meta:
        verbose_name = _('remote work document')
        verbose_name_plural = _('remote work documents')

    document_id = models.PositiveIntegerField(verbose_name=_('document ID'))
    absent_name = models.CharField(max_length=250, verbose_name=_('absent name'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    number_of_days = models.PositiveIntegerField(verbose_name=_('number of days'))
    decisive_name = models.CharField(max_length=250, verbose_name=_('decisive name'))
    date_of_completion = models.DateField(verbose_name=_('date of completion'))
    registration_number = models.CharField(max_length=20, verbose_name=_('registration number'))
    department_name = models.CharField(max_length=250, null=True, blank=True,
                                        verbose_name=_('department name'))
    department_manager_name = models.CharField(max_length=250, null=True, blank=True,
                                                verbose_name=_('department manager name'))
    city = models.CharField(max_length=50, verbose_name=_('city'))
    address_country = models.CharField(max_length=50, verbose_name=_('country'))
    address_street = models.CharField(max_length=100, verbose_name=_('street'))
    address_house_number = models.CharField(max_length=10, verbose_name=_('house number'))
    address_apartment_number = models.CharField(max_length=10, blank=True, null=True,
                                                verbose_name=_('apartment number'))
    address_postal_code = models.CharField(max_length=20, verbose_name=_('postal code'))
    address_city = models.CharField(max_length=50, verbose_name=_('city'))

    def __str__(self):
        return f'{_("Document")} {self.absent_name} - {self.start_date}-{self.end_date}'


class RemoteWork(models.Model):
    class Meta:
        verbose_name = _('remote work')
        verbose_name_plural = _('remote works')
        permissions = (
            ('moderate_remote_work', 'Can moderate remote works'),
            ('view_remote_work_document', 'Can view remote work document'),
        )

    PENDING_STATUS = 1
    ACCEPTED_STATUS = 2
    REJECTED_STATUS = 3
    CANCELED_STATUS = 4
    CANCELED_BY_DECISIVE_STATUS = 5
    PENDING_TO_CANCEL_STATUS = 6
    PENDING_TO_FINISH_EARLIER_STATUS = 7

    STATUS_CHOICES = (
        (PENDING_STATUS, _('Pending')),
        (ACCEPTED_STATUS, _('Accepted')),
        (REJECTED_STATUS, _('Rejected')),
        (CANCELED_STATUS, _('Canceled')),
        (CANCELED_BY_DECISIVE_STATUS, _('Canceled by decisive person')),
        (PENDING_TO_CANCEL_STATUS, _('Pending to cancel')),
        (PENDING_TO_FINISH_EARLIER_STATUS, _('Pending to finish earlier')),
    )

    absent = models.ForeignKey(User, related_name='RWEmployee', on_delete=models.PROTECT, verbose_name=_('absent'))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(verbose_name=_('end date'))
    number_of_days = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                                verbose_name=_('number of days'))

    country = models.CharField(max_length=50, verbose_name=_('country'))
    street = models.CharField(max_length=100, verbose_name=_('street'))
    house_number = models.CharField(max_length=10, verbose_name=_('house number'))
    apartment_number = models.CharField(max_length=10, blank=True,
                                        verbose_name=_('apartment number'))
    postal_code = models.CharField(max_length=20, verbose_name=_('postal code'))
    city = models.CharField(max_length=50, verbose_name=_('city'))

    decisive_person = models.ForeignKey(User, related_name='RWDecisive', default=None, 
                                        on_delete=models.PROTECT, null=True, verbose_name=_('decisive person'))
    message_for_decisive_person = models.TextField(null=False, blank=True, verbose_name=_('message for decisive person'))
    date_of_completion = models.DateField(default=timezone.now, verbose_name=_('date of completion'))
    
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING_STATUS, verbose_name=_('status'))
    status_changed_by = models.ForeignKey(User, related_name='RWStatusChangedBy', default=None, 
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('status changed by'))
    last_status_change_time = models.DateTimeField(default=None, null=True, blank=True, 
                                                    verbose_name=_('last status change time'))
    rejection_reason = models.TextField(null=False, blank=True, verbose_name=_('rejection reason'))

    pending_end_date = models.DateField(null=True, blank=True, verbose_name=_('pending end date'))
    pending_number_of_days = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)],
                                            verbose_name=_('pending number of days'))

    document = models.OneToOneField(RemoteWorkDocument, on_delete=models.SET_NULL, default=None,
                                    null=True, blank=True, related_name='remote_work', verbose_name=_('document'))
    
    def clean(self):
        validate_start_earlier_than_or_equal_end_date(self.start_date, self.end_date)
        validate_start_later_than_or_equal_date_of_completion(self.start_date, self.date_of_completion)
        self.validate_decisive_person()

    
    def validate_decisive_person(self):
        try:
            employee = self.absent.employee
        except Employee.DoesNotExist:
            raise ValidationError(
                _('You need to have employee assigned in order to plan remote work.'),
                code='employee_not_assigned'
            )
        else:
            supervisors_ids = employee.get_supervisor_users_ids()

            if self.decisive_person.id not in supervisors_ids:
                raise ValidationError(
                    _('You chose wrong decisive person.'),
                    code='wrong_decisive_person',
                )

    @staticmethod
    def validate_user_remote_work_one_at_a_time(user, start_date, end_date, remote_work_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date) + \
                    get_colliding_special_leaves_str(user, start_date, end_date) + \
                    get_colliding_remote_works_str(user, start_date, end_date, remote_work_id)

        handle_colliding_absences_str(colliding_absences_str)
    
    @staticmethod
    def get_colliding_absences_info(user, start_date, end_date, remote_work_id=None):
        colliding_absences_str = get_colliding_absences_str(user, start_date, end_date) + \
                    get_colliding_vacation_leaves_str(user, start_date, end_date) + \
                    get_colliding_special_leaves_str(user, start_date, end_date) + \
                    get_colliding_remote_works_str(user, start_date, end_date, remote_work_id)

        return colliding_absences_str
    
    @staticmethod
    def validate_pending_number_of_days(start_date, pending_end_date, pending_number_of_days):
        number_of_days_in_date_range = (pending_end_date - start_date).days + 1

        if number_of_days_in_date_range < pending_number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )

    @staticmethod
    def validate_number_of_days(start_date, end_date, number_of_days):
        number_of_days_in_date_range = (end_date - start_date).days + 1

        if number_of_days_in_date_range < number_of_days:
            raise ValidationError(
                _('The number of days between start date and end date cannot be lower than the number of days entered.'),
                code='date_range_days_lower_than_entered_days',
            )
    
    def can_update(self):
        return general_functions.current_date() <= self.start_date and self.is_pending()

    def can_finish_earlier(self):
        today = general_functions.current_date()
        return today > self.start_date and today <= self.end_date and self.is_accepted()

    def can_cancel(self):
        if not self.is_accepted():
            return False
        
        return general_functions.current_date() <= self.start_date

    def can_delete(self):
        return self.is_pending()

    def can_change_decision(self):
        if not self.is_accepted() and not self.is_rejected():
            return False
        
        return general_functions.current_date() < self.start_date

    def is_pending(self):
        return self.status == RemoteWork.PENDING_STATUS

    def is_accepted(self):
        return self.status == RemoteWork.ACCEPTED_STATUS

    def is_rejected(self):
        return self.status == RemoteWork.REJECTED_STATUS \
            or self.status == RemoteWork.CANCELED_BY_DECISIVE_STATUS

    def is_canceled(self):
        return self.status == RemoteWork.CANCELED_STATUS

    def is_finished(self):
        today = general_functions.current_date()
        return today > self.end_date and self.is_accepted()

    def is_pending_to_cancel(self):
        return self.status == RemoteWork.PENDING_TO_CANCEL_STATUS
    
    def is_pending_to_finish_earlier(self):
        return self.status == RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS

    def create_document(self):
        with transaction.atomic():
            document = RemoteWorkDocument(
                start_date=self.start_date,
                end_date=self.end_date,
                number_of_days=self.number_of_days,
                date_of_completion=self.date_of_completion,
                document_id=self.id,
                absent_name=self.absent.profile.get_name(),
                decisive_name=self.decisive_person.profile.get_name(),
                registration_number=self.absent.employee.registration_number,
                department_name=self.absent.employee.get_department_name(),
                department_manager_name=self.absent.employee.get_department_manager_name(),
                city=global_live_settings.company.city,
                address_country=self.country,
                address_street=self.street,
                address_house_number=self.house_number,
                address_apartment_number=self.apartment_number,
                address_postal_code=self.postal_code,
                address_city=self.city
            )
            
            try:
                document.full_clean()
            except ValidationError as e:
                raise e
            else:
                document.remote_work = self
                document.save()

                self.document = document
                self.save()

    def save(self, *args, **kwargs):
        if self.is_pending() or self.is_pending_to_cancel() or self.is_pending_to_finish_earlier():
            self.rejection_reason = ''

        if self.is_pending():
            self.status_changed_by = None
            self.last_status_change_time = None

        super(RemoteWork, self).save(*args, **kwargs)

    def name(self):
        return f'{_("Remote work")}'

    def __str__(self):
        return f'{self.absent} - {self.start_date}-{self.end_date}'
    
    @staticmethod
    def get_number_of_remote_works_to_moderate(decisive_person):
        return RemoteWork.objects.filter(status__in=(
                                                RemoteWork.PENDING_STATUS,
                                                RemoteWork.PENDING_TO_CANCEL_STATUS,
                                                RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS,
                                            ),
                                            decisive_person=decisive_person).count()
    
    @staticmethod
    def get_status_representation(status):
        for status_choice in RemoteWork.STATUS_CHOICES:
            if status_choice[0] == status:
                return status_choice[1]

        raise ValueError('Wrong remote work status was given.')
    
    @staticmethod
    def get_statuses():
        return {
            'PENDING': {
                'value': RemoteWork.PENDING_STATUS,
                'representation': RemoteWork.get_status_representation(RemoteWork.PENDING_STATUS),
            },
            'ACCEPTED': {
                'value': RemoteWork.ACCEPTED_STATUS,
                'representation': RemoteWork.get_status_representation(RemoteWork.ACCEPTED_STATUS),
            },
            'REJECTED': {
                'value': RemoteWork.REJECTED_STATUS,
                'representation': RemoteWork.get_status_representation(RemoteWork.REJECTED_STATUS),
            },
            'CANCELED': {
                'value': RemoteWork.CANCELED_STATUS,
                'representation': RemoteWork.get_status_representation(RemoteWork.CANCELED_STATUS),
            },
            'CANCELED_BY_DECISIVE': {
                'value': RemoteWork.CANCELED_BY_DECISIVE_STATUS,
                'representation': RemoteWork.get_status_representation(
                        RemoteWork.CANCELED_BY_DECISIVE_STATUS
                    ),
            },
            'PENDING_TO_CANCEL': {
                'value': RemoteWork.PENDING_TO_CANCEL_STATUS,
                'representation': RemoteWork.get_status_representation(
                        RemoteWork.PENDING_TO_CANCEL_STATUS
                    ),
            },
            'PENDING_TO_FINISH_EARLIER': {
                'value': RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS,
                'representation': RemoteWork.get_status_representation(
                        RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS
                    ),
            },
        }

    @staticmethod
    def fill_query_args_absent_first_last_name(kwargs, first_name, last_name):
        kwargs['absent__in'] = []
        absent_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if absent_users:
            kwargs['absent__in'] = absent_users

    @staticmethod
    def fill_query_args_decisive_first_last_name(kwargs, first_name, last_name):
        kwargs['decisive_person__in'] = []
        decisive_users = User.objects.filter(first_name__icontains=first_name, 
                                            last_name__icontains=last_name)
        if decisive_users:
            kwargs['decisive_person__in'] = decisive_users

    @staticmethod
    def fill_query_args_end_date__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'end_date__gte', date)

    @staticmethod
    def fill_query_args_start_date__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'start_date__lte', date)

    @staticmethod
    def fill_query_args_date_of_completion__gte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__gte', date)

    @staticmethod
    def fill_query_args_date_of_completion__lte(kwargs, date):
        general_functions.fill_date_kwarg(kwargs, 'date_of_completion__lte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__gte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__gte', date)

    @staticmethod
    def fill_query_args_last_status_change_time__lte(kwargs, date):
        general_functions.fill_datetime_kwarg(kwargs, 'last_status_change_time__lte', date)
    
    @staticmethod
    def fill_query_args_status(kwargs, value):
        try:
            leave_status = int(value)
        except ValueError:
            pass
        else:
            kwargs['status'] = leave_status

    @staticmethod
    def fill_query_args_status_one_of(args, kwargs, value, statuses):
        try:
            remote_work_status = int(value)
        except ValueError:
            args.append(RemoteWork.get_statuses_args(statuses))
        else:
            if remote_work_status in statuses:
                kwargs['status'] = remote_work_status
            else:
                args.append(RemoteWork.get_statuses_args(statuses))

    @staticmethod
    def get_statuses_args(statuses):
        query = Q(status=statuses[0])

        for status in statuses[1:]:
            query |= Q(status=status)

        return query
    
    @staticmethod
    def fill_query_args_remote_work_id(kwargs, value):
        try:
            kwargs['id'] = int(value)
        except ValueError:
            pass


def validate_start_earlier_than_or_equal_end_date(start_date, end_date):
    if start_date > end_date:
        raise ValidationError(_('The start date must be no later than the end date.'),
                            code='start_date_later_than_end_date')


def validate_start_later_than_or_equal_date_of_completion(start_date, date_of_completion):
    if date_of_completion > start_date:
        raise ValidationError(_('The date of completion must be no later than the start date.'),
                            code='date_of_completion_later_than_start_date')


def handle_colliding_absences_str(colliding_absences_str):
    if colliding_absences_str:
        raise ValidationError(
            _('At the given date range there is already absence planned! %(colliding_absences)s'),
            code='user_absence_already_planned',
            params={'colliding_absences': '(' + colliding_absences_str + ')'}
        )


def get_colliding_absences_str(user, start_date, end_date, absence_id=None):
    colliding_absences = Absence.objects.exclude(id=absence_id).filter(Q(start_date__lte=end_date) &
                        Q(end_date__gte=start_date), absent=user)
    
    colliding_absences_str = ''
    for absence in colliding_absences:
        colliding_absences_str += get_absence_str(absence.absence_type.text,
                                    absence.start_date, absence.end_date)
    
    return colliding_absences_str


def get_colliding_vacation_leaves_str(user, start_date, end_date, vacation_leave_id=None):
    colliding_vacation_leaves = VacationLeave.objects.exclude(id=vacation_leave_id).filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date), 
        absent=user, status__in=(VacationLeave.ACCEPTED_STATUS, VacationLeave.PENDING_TO_CANCEL_STATUS,
                                    VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS,)
    )

    colliding_vacation_leaves_str = ''
    for vacation_leave in colliding_vacation_leaves:
        colliding_vacation_leaves_str += get_absence_str(_('Vacation leave'),
                                    vacation_leave.start_date, vacation_leave.end_date)
    
    return colliding_vacation_leaves_str


def get_colliding_special_leaves_str(user, start_date, end_date, special_leave_id=None):
    colliding_special_leaves = SpecialLeave.objects.exclude(id=special_leave_id).filter(
        Q(start_date__lte=end_date) &
        Q(end_date__gte=start_date), 
        absent=user, status__in=(SpecialLeave.ACCEPTED_STATUS, SpecialLeave.CONFIRMED_STATUS,
                                SpecialLeave.PENDING_TO_CANCEL_STATUS,
                                SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS)
    )

    colliding_special_leaves_str = ''
    for special_leave in colliding_special_leaves:
        colliding_special_leaves_str += get_absence_str(_('Special leave'),
                                    special_leave.start_date, special_leave.end_date)
    
    return colliding_special_leaves_str


def get_colliding_remote_works_str(user, start_date, end_date, remote_work_id=None):
    colliding_remote_works = RemoteWork.objects.exclude(id=remote_work_id).filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date), 
        absent=user, status__in=(RemoteWork.ACCEPTED_STATUS, RemoteWork.PENDING_TO_CANCEL_STATUS,
                                    RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS,)
    )

    colliding_remote_works_str = ''
    for remote_work in colliding_remote_works:
        colliding_remote_works_str += get_absence_str(_('Remote work'),
                                    remote_work.start_date, remote_work.end_date)
    
    return colliding_remote_works_str


def get_absence_str(absence_type, start_date, end_date):
    return str(_('Type')) + ': ' + str(absence_type) + ' ' + str(_('From')) + ': ' + \
        str(start_date) + ', ' + str(_('To')) + ': ' + str(end_date) + '; '
