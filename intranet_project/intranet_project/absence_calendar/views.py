from datetime import datetime, timedelta
from calendar import monthrange

from intranet_project import general_functions

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from .models import (
    Absence, AbsenceType, VacationLeave, SpecialLeave, VacationLeaveType,
    SpecialLeaveReason, Event, RemoteWork
)
from company_structure.models import Employee
from .forms import (
    AbsenceCreateForm, VacationLeaveCreateForm, SpecialLeaveCreateForm,
    AbsenceUpdateForm, VacationLeaveUpdateForm, SpecialLeaveUpdateForm,
    AbsenceFinishEarlierForm, VacationLeaveFinishEarlierForm, SpecialLeaveFinishEarlierForm,
    SpecialLeaveUpdateConfirmationDocumentDataForm, EventCreateForm, EventUpdateForm,
    AbsenceByManagerCreateForm, RemoteWorkCreateForm, RemoteWorkUpdateForm, RemoteWorkFinishEarlierForm
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import formats
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import View, ListView, CreateView, UpdateView, DetailView, DeleteView
from django.db.models import Q
from django.core.exceptions import ValidationError
from . import signals
from django.contrib.auth.decorators import permission_required
from django.db.models import F

from live_settings.global_live_settings import global_live_settings


class EventDetailView(DetailView):
    model = Event
    template_name = 'absence_calendar/event_detail.html'


class EventCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'absence_calendar.add_event'
    model = Event
    template_name = 'absence_calendar/event_create.html'
    form_class = EventCreateForm

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('absence_calendar:event_detail', kwargs={'pk': self.object.pk})


class EventUpdateView(PermissionRequiredMixin, UserPassesTestMixin, UpdateView):
    permission_required = 'absence_calendar.change_event'
    model = Event
    template_name = 'absence_calendar/event_update.html'
    form_class = EventUpdateForm

    def test_func(self):
        event = self.get_object()

        return self.request.user == event.created_by
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:event_detail', kwargs={'pk': self.object.pk})


class EventDeleteView(PermissionRequiredMixin, UserPassesTestMixin, DeleteView):
    permission_required = 'absence_calendar.delete_event'
    model = Event
    template_name = 'absence_calendar/event_confirm_delete.html'
    success_url = '/'

    def test_func(self):
        event = self.get_object()

        return self.request.user == event.created_by


class AbsenceDetailView(DetailView):
    model = Absence
    template_name = 'absence_calendar/absence_detail.html'


class AbsenceCreateView(LoginRequiredMixin, CreateView):
    model = Absence
    template_name = 'absence_calendar/absence_create.html'
    form_class = AbsenceCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absent'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.absent = self.request.user
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:absence_detail', kwargs={'pk': self.object.pk})


class AbsenceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Absence
    template_name = 'absence_calendar/absence_update.html'
    form_class = AbsenceUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absence'] = self.object
        return kwargs

    def test_func(self):
        absence = self.get_object()

        if not absence.can_update():
            return False

        return self.request.user == absence.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:absence_detail', kwargs={'pk': self.object.pk})


class AbsenceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Absence
    template_name = 'absence_calendar/absence_confirm_delete.html'
    success_url = '/'

    def test_func(self):
        absence = self.get_object()

        if not absence.can_delete():
            return False

        return self.request.user == absence.absent


class AbsenceFinishEarlierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Absence
    template_name = 'absence_calendar/absence_finish_earlier.html'
    form_class = AbsenceFinishEarlierForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['start_date'] = self.object.start_date
        kwargs['end_date'] = self.object.end_date
        
        return kwargs

    def test_func(self):
        absence = self.get_object()

        if not absence.can_finish_earlier():
            return False

        return self.request.user == absence.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:absence_detail', kwargs={'pk': self.object.pk})


class AbsenceByManagerCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Absence
    template_name = 'absence_calendar/absence_by_manager.html'
    form_class = AbsenceByManagerCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        
        return kwargs

    def test_func(self):
        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:absence_detail', kwargs={'pk': self.object.pk})


class AbsenceByManagerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Absence
    template_name = 'absence_calendar/absence_by_manager_confirm_delete.html'

    def test_func(self):
        absence = self.get_object()

        if not absence.can_delete():
            return False

        return self.request.user.id in absence.absent.employee.get_supervisor_users_ids()

    def get_success_url(self):
        absence = self.get_object()

        return reverse_lazy('absence_calendar:absence_calendar', 
                kwargs={
                    'year': absence.start_date.year,
                    'month': absence.start_date.month
                })


class UserAbsencesListView(LoginRequiredMixin, ListView):
    model = Absence
    template_name = 'absence_calendar/user_absences.html'
    context_object_name = 'absences'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(UserAbsencesListView, self).get_context_data(**kwargs)
        context['absence_types'] = AbsenceType.objects.all()

        return context

    def get_queryset(self):
        kwargs = self.get_query_kwargs()

        return Absence.objects.filter(absent=self.request.user, **kwargs).order_by('-start_date', '-end_date')

    def get_query_kwargs(self):
        kwargs = {}
        
        if self.request.GET.get('absenceRangeDateStart', None) is not None:
            Absence.fill_query_args_end_date__gte(kwargs, self.request.GET['absenceRangeDateStart'])

        if self.request.GET.get('absenceRangeDateEnd', None) is not None:
            Absence.fill_query_args_start_date__lte(kwargs, self.request.GET['absenceRangeDateEnd'])

        if self.request.GET.get('absenceType', None) is not None:
            Absence.fill_query_args_absence_type(kwargs, self.request.GET['absenceType'])
        
        return kwargs

#######################################################################
# VacationLeave
#######################################################################

class VacationLeaveDetailView(UserPassesTestMixin, DetailView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_detail.html'

    def test_func(self):
        vacation_leave = self.get_object()

        if vacation_leave.is_accepted():
            return True
        else:
            return self.request.user == vacation_leave.absent or \
                self.request.user == vacation_leave.decisive_person


class VacationLeaveCreateView(LoginRequiredMixin, CreateView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_create.html'
    form_class = VacationLeaveCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absent'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.absent = self.request.user
        self.object = form.save()
        signals.vacation_leave_pending.send(sender=VacationLeave, instance=self.object)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:vacation_leave_detail', kwargs={'pk': self.object.pk})


class VacationLeaveUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_update.html'
    form_class = VacationLeaveUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absence'] = self.object
        return kwargs

    def form_valid(self, form):
        was_accepted = True if self.object.is_accepted() else False
        vacation_leave_b4_update = get_object_or_404(VacationLeave, id=self.object.id)

        form.instance.status = VacationLeave.PENDING_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()

        if was_accepted:
            signals.accepted_vacation_leave_updated.send(sender=VacationLeave, instance=self.object)
        else:
            decisive_person_changed = form.instance.decisive_person != \
                                        vacation_leave_b4_update.decisive_person

            if decisive_person_changed:
                signals.vacation_leave_decisive_changed.send(sender=VacationLeave,
                                                            instance=vacation_leave_b4_update)
                signals.vacation_leave_pending.send(sender=VacationLeave, instance=self.object)
        
        return super().form_valid(form)

    def test_func(self):
        vacation_leave = self.get_object()

        if not vacation_leave.can_update():
            return False

        return self.request.user == vacation_leave.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:vacation_leave_detail', kwargs={'pk': self.object.pk})

    
class VacationLeaveDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_confirm_delete.html'
    success_url = '/'

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        signals.vacation_leave_deleted.send(sender=VacationLeave, instance=self.object)
        
        return super(VacationLeaveDeleteView, self).delete(*args, **kwargs)

    def test_func(self):
        vacation_leave = self.get_object()

        if not vacation_leave.can_delete():
            return False

        return self.request.user == vacation_leave.absent


class VacationLeaveCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_confirm_cancel.html'
    fields = ['message_for_decisive_person',]

    def form_valid(self, form):
        form.instance.status = VacationLeave.PENDING_TO_CANCEL_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.vacation_leave_pending_to_cancel.send(sender=VacationLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        vacation_leave = self.get_object()

        if not vacation_leave.can_cancel():
            return False

        return self.request.user == vacation_leave.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:vacation_leave_detail', kwargs={'pk': self.object.pk})


class VacationLeaveFinishEarlierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leave_finish_earlier.html'
    form_class = VacationLeaveFinishEarlierForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['start_date'] = self.object.start_date
        kwargs['end_date'] = self.object.end_date
        
        return kwargs

    def form_valid(self, form):
        form.instance.status = VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.vacation_leave_pending_to_finish_earlier.send(sender=VacationLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        vacation_leave = self.get_object()

        if not vacation_leave.can_finish_earlier():
            return False

        return self.request.user == vacation_leave.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:vacation_leave_detail', kwargs={'pk': self.object.pk})


class VacationLeavesModerationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leaves_moderation.html'
    context_object_name = 'vacation_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(VacationLeavesModerationListView, self).get_context_data(**kwargs)
        vacation_leaves_to_moderate = VacationLeave.get_number_of_vacation_leaves_to_moderate(self.request.user)
        special_leaves_to_moderate = SpecialLeave.get_number_of_special_leaves_to_moderate(self.request.user)
        remote_works_to_moderate = RemoteWork.get_number_of_remote_works_to_moderate(self.request.user)
        context['vacation_leaves_to_moderate'] = '99+' if vacation_leaves_to_moderate > 99 \
                                                    else str(vacation_leaves_to_moderate)
        context['special_leaves_to_moderate'] = '99+' if special_leaves_to_moderate > 99 \
                                                    else str(special_leaves_to_moderate)
        context['remote_works_to_moderate'] = '99+' if remote_works_to_moderate > 99 \
                                                    else str(remote_works_to_moderate)
        return context

    def get_queryset(self):
        return VacationLeave.objects.filter(status__in=(
                                                VacationLeave.PENDING_STATUS,
                                                VacationLeave.PENDING_TO_CANCEL_STATUS,
                                                VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS
                                            ),
                                            decisive_person=self.request.user).order_by('-date_of_completion',
                                            '-start_date', '-end_date', 'absent')

    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class VacationLeaveAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this vacation leave has already been made.'),}, status=200)

        colliding_absences_str = VacationLeave.get_colliding_absences_info(vacation_leave.absent,
                                    vacation_leave.start_date, vacation_leave.end_date, vacation_leave.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        vacation_leave.status = VacationLeave.ACCEPTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(vacation_leave, _('Vacation leave was accepted.'))

        if context['ok']:
            signals.vacation_leave_accepted.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class VacationLeaveRejectAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this vacation leave has already been made.'),}, status=200)

        vacation_leave.status = VacationLeave.REJECTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        vacation_leave.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(vacation_leave, _('Vacation leave was rejected.'))

        if context['ok']:
            signals.vacation_leave_rejected.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class VacationLeaveAcceptCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this vacation leave cancelation has already been made.'),}, status=200)

        vacation_leave.status = VacationLeave.CANCELED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(vacation_leave, _('Vacation leave cancelation was accepted.'))

        if context['ok']:
            signals.vacation_leave_canceled.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class VacationLeaveRejectCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this vacation leave cancelation has already been made.'),}, status=200)

        vacation_leave.status = VacationLeave.ACCEPTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            vacation_leave.rejection_reason = request.POST['reason']
        else:
            vacation_leave.rejection_reason = _('The request for cancelation was rejected.')

        context = get_leave_status_change_context(vacation_leave, _('Vacation leave cancelation was rejected.'))

        if context['ok']:
            signals.vacation_leave_cancelation_rejected.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class VacationLeaveAcceptFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish vacation leave earlier has already been made.'),},
                status=200
                )

        vacation_leave.end_date = vacation_leave.pending_end_date
        vacation_leave.number_of_days = vacation_leave.pending_number_of_days
        vacation_leave.status = VacationLeave.ACCEPTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(vacation_leave,
                    _('Request to finish vacation leave earlier was accepted.'))

        if context['ok']:
            signals.vacation_leave_finished_earlier.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class VacationLeaveRejectFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish vacation leave earlier has already been made.'),},
                status=200
                )

        vacation_leave.status = VacationLeave.ACCEPTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            vacation_leave.rejection_reason = request.POST['reason']
        else:
            vacation_leave.rejection_reason = _('The request for vacation leave to finish earlier was rejected.')

        context = get_leave_status_change_context(vacation_leave,
                    _('Request to finish vacation leave earlier was rejected.'))

        if context['ok']:
            signals.vacation_leave_request_to_finish_earlier_rejected.send(
                sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class VacationLeavesPreviouslyProcessedListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leaves_previously_processed.html'
    context_object_name = 'vacation_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(VacationLeavesPreviouslyProcessedListView, self).get_context_data(**kwargs)
        context['status_choices'] = VacationLeave.get_statuses()
        context['vacation_leave_types'] = VacationLeaveType.objects.all()

        return context

    def get_queryset(self):
        args = []
        kwargs = {}
        self.fill_query_args(args, kwargs)

        return VacationLeave.objects.filter(decisive_person=self.request.user, *args, **kwargs
                            ).order_by('-date_of_completion', '-start_date', '-end_date', 'absent')

    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            VacationLeave.fill_query_args_absent_first_last_name(kwargs,
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))
        
        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            VacationLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            VacationLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])
        
        if self.request.GET.get('leaveForYear', None) is not None:
            VacationLeave.fill_query_args_leave_for_year(kwargs, self.request.GET['leaveForYear'])

        if self.request.GET.get('vacationLeaveType', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_type(kwargs, self.request.GET['vacationLeaveType'])

        statuses_without_filter = [VacationLeave.ACCEPTED_STATUS, VacationLeave.REJECTED_STATUS, 
                                    VacationLeave.CANCELED_BY_DECISIVE_STATUS, VacationLeave.CANCELED_STATUS,]

        if self.request.GET.get('leaveStatus', None) is not None:
            VacationLeave.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(VacationLeave.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('vacationLeaveId', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_id(kwargs, self.request.GET['vacationLeaveId'])
    
    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class VacationLeaveChangeDecisionAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this vacation leave can not be changed.'),}, status=200)

        if not vacation_leave.is_rejected():
            return JsonResponse({'ok': False, 'message': 
                _('This vacation leave is not rejected.'),}, status=200)

        colliding_absences_str = VacationLeave.get_colliding_absences_info(vacation_leave.absent,
                                    vacation_leave.start_date, vacation_leave.end_date, vacation_leave.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        vacation_leave.status = VacationLeave.ACCEPTED_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(vacation_leave, _('Vacation leave was accepted.'))
        context['status_change_time'] = formats.date_format(vacation_leave.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.vacation_leave_decision_changed_accepted.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class VacationLeaveChangeDecisionRejectAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        vacation_leave = get_object_or_404(VacationLeave, id=id)

        if not vacation_leave.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this vacation leave can not be changed.'),}, status=200)

        if not vacation_leave.is_accepted():
            return JsonResponse({'ok': False, 'message': 
                _('This vacation leave is not accepted.'),}, status=200)

        vacation_leave.status = VacationLeave.CANCELED_BY_DECISIVE_STATUS
        vacation_leave.status_changed_by = request.user
        vacation_leave.last_status_change_time = general_functions.current_datetime()
        vacation_leave.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(vacation_leave, _('Vacation leave was rejected.'))
        context['status_change_time'] = formats.date_format(vacation_leave.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.vacation_leave_decision_changed_rejected.send(sender=VacationLeave, instance=vacation_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        vacation_leave = get_object_or_404(VacationLeave, id=self.request.POST['id'])

        if self.request.user == vacation_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_vacation_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class VacationLeavesApplicationsListView(PermissionRequiredMixin, ListView):
    permission_required = 'absence_calendar.view_vacation_leave_document'
    model = VacationLeave
    template_name = 'absence_calendar/vacation_leaves_applications.html'
    context_object_name = 'vacation_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(VacationLeavesApplicationsListView, self).get_context_data(**kwargs)
        context['status_choices'] = VacationLeave.get_statuses()
        context['vacation_leave_types'] = VacationLeaveType.objects.all()

        return context

    def get_queryset(self):
        kwargs = {}
        args = []
        self.fill_query_args(args, kwargs)

        order_args = []
        self.fill_order_args(order_args)

        return VacationLeave.objects.filter(*args, **kwargs).order_by(*order_args)
    
    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            VacationLeave.fill_query_args_absent_first_last_name(kwargs,
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))
            
        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            VacationLeave.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))
        
        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            VacationLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            VacationLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        if self.request.GET.get('lastStatusChangeDateStart', None) is not None:
            VacationLeave.fill_query_args_last_status_change_time__gte(
                kwargs, self.request.GET['lastStatusChangeDateStart'] + ' 00:00')

        if self.request.GET.get('lastStatusChangeDateEnd', None) is not None:
            VacationLeave.fill_query_args_last_status_change_time__lte(
                kwargs, self.request.GET['lastStatusChangeDateEnd'] + ' 23:59')
        
        if self.request.GET.get('leaveForYear', None) is not None:
            VacationLeave.fill_query_args_leave_for_year(kwargs, self.request.GET['leaveForYear'])

        if self.request.GET.get('vacationLeaveType', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_type(kwargs, self.request.GET['vacationLeaveType'])

        statuses_without_filter = [VacationLeave.ACCEPTED_STATUS, VacationLeave.CANCELED_STATUS, 
                                    VacationLeave.CANCELED_BY_DECISIVE_STATUS, VacationLeave.PENDING_TO_CANCEL_STATUS,
                                    VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS, VacationLeave.PENDING_STATUS,
                                    VacationLeave.REJECTED_STATUS]

        if self.request.GET.get('leaveStatus', None) is not None:
            VacationLeave.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(VacationLeave.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('vacationLeaveId', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_id(kwargs, self.request.GET['vacationLeaveId'])

    def fill_order_args(self, args):
        if self.request.GET.get('orderCol', None) is not None and \
            self.request.GET.get('orderDirection', None) is not None:
            order_column = self.request.GET['orderCol']
            order_direction = self.request.GET['orderDirection']
            direction_sign = ''

            if order_direction == 'desc':
                direction_sign = '-'
            
            if order_column == 'absent':
                args.append(direction_sign + 'absent__last_name')
                args.append(direction_sign + 'absent__first_name')
            elif order_column == 'decisive':
                args.append(direction_sign + 'decisive_person__last_name')
                args.append(direction_sign + 'decisive_person__first_name')
            elif order_column == 'leaveDateStart':
                args.append(direction_sign + 'start_date')
            elif order_column == 'leaveDateEnd':
                args.append(direction_sign + 'end_date')
            elif order_column == 'completionDate':
                args.append(direction_sign + 'date_of_completion')
            elif order_column == 'leaveForYear':
                args.append(direction_sign + 'leave_for_year')
            elif order_column == 'vacationLeaveType':
                args.append(direction_sign + 'vacation_leave_type')
            elif order_column == 'lastStatusChangeDate':
                args.append(direction_sign + 'last_status_change_time')
        else:
            args.append(F('last_status_change_time').desc(nulls_first=True))
            args.append('-date_of_completion')
            args.append('-start_date')
            args.append('-end_date')
            args.append('absent')


class VacationLeaveApplicationDetailView(UserPassesTestMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'absence_calendar.view_vacation_leave_document'
    model = VacationLeave
    context_object_name = 'vacation_leave'
    template_name = 'absence_calendar/vacation_leave_application_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['city'] = global_live_settings.company.city

        return context

    def test_func(self):
        vacation_leave = self.get_object()

        if not vacation_leave.is_accepted() and not vacation_leave.is_pending_to_cancel() \
            and not vacation_leave.is_pending_to_finish_earlier():
            return False

        return True


@permission_required('absence_calendar.view_vacation_leave_document')
def vacation_leave_application_pdf(request, vacation_leave_id):
    vacation_leave = get_object_or_404(VacationLeave, id=vacation_leave_id)

    if not vacation_leave.is_accepted() and not vacation_leave.is_pending_to_cancel() \
        and not vacation_leave.is_pending_to_finish_earlier():
        return HttpResponseForbidden()

    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {
        'vacation_leave': vacation_leave,
        'download_mode': True,
        'city': global_live_settings.company.city,
    }
    template_path = 'absence_calendar/vacation_leave_application_detail.html'
    filename = f'{_("Vacation leave")} - {vacation_leave_id}'
    
    return general_functions.get_pdf_response(options, context, template_path, filename)


@permission_required('absence_calendar.view_vacation_leave_document')
def vacation_leaves_applications_pdf(request):
    vacation_leaves = []

    if request.GET.get('id', None):
        for vacation_leave_id in request.GET.getlist('id'):
            vacation_leave = get_object_or_404(VacationLeave, id=vacation_leave_id)

            if not vacation_leave.is_accepted() and not vacation_leave.is_pending_to_cancel() \
                and not vacation_leave.is_pending_to_finish_earlier():
                return HttpResponseForbidden()

            vacation_leaves.append(vacation_leave)
    
    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {'vacation_leaves': vacation_leaves, 'city': global_live_settings.company.city,}
    template_path = 'absence_calendar/vacation_leaves_applications_pdf.html'
    filename = _('Vacation leaves')

    return general_functions.get_pdf_response(options, context, template_path, filename)


class UserVacationLeavesListView(LoginRequiredMixin, ListView):
    model = VacationLeave
    template_name = 'absence_calendar/user_vacation_leaves.html'
    context_object_name = 'vacation_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(UserVacationLeavesListView, self).get_context_data(**kwargs)
        context['status_choices'] = VacationLeave.get_statuses()
        context['vacation_leave_types'] = VacationLeaveType.objects.all()
        context['sum_of_vacation_days'] = 0

        for vacation_leave in context['vacation_leaves']:
            if vacation_leave.is_accepted() or vacation_leave.is_pending_to_cancel() or \
                vacation_leave.is_pending_to_finish_earlier():
                context['sum_of_vacation_days'] += vacation_leave.number_of_days

        return context

    def get_queryset(self):
        kwargs = self.get_query_args()

        return VacationLeave.objects.filter(absent=self.request.user, **kwargs).order_by(
                                        '-date_of_completion', '-start_date', '-end_date')

    def get_query_args(self):
        kwargs = {}

        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            VacationLeave.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))

        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            VacationLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            VacationLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            VacationLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])
        
        if self.request.GET.get('leaveForYear', None) is not None:
            VacationLeave.fill_query_args_leave_for_year(kwargs, self.request.GET['leaveForYear'])

        if self.request.GET.get('vacationLeaveType', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_type(kwargs, self.request.GET['vacationLeaveType'])

        if self.request.GET.get('leaveStatus', None) is not None:
            VacationLeave.fill_query_args_status(kwargs, self.request.GET['leaveStatus'])

        if self.request.GET.get('vacationLeaveId', None) is not None:
            VacationLeave.fill_query_args_vacation_leave_id(kwargs, self.request.GET['vacationLeaveId'])

        return kwargs

#######################################################################
# SpecialLeave
#######################################################################

class SpecialLeaveDetailView(UserPassesTestMixin, DetailView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_detail.html'

    def test_func(self):
        special_leave = self.get_object()

        if special_leave.is_accepted() or special_leave.is_confirmed():
            return True
        else:
            return self.request.user == special_leave.absent or \
                self.request.user == special_leave.decisive_person

    
class SpecialLeaveCreateView(LoginRequiredMixin, CreateView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_create.html'
    form_class = SpecialLeaveCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absent'] = self.request.user
        return kwargs
        
    def form_valid(self, form):
        form.instance.absent = self.request.user
        self.object = form.save()
        signals.special_leave_pending.send(sender=SpecialLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:special_leave_detail', kwargs={'pk': self.object.pk})


class SpecialLeaveUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_update.html'
    form_class = SpecialLeaveUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absence'] = self.object
        return kwargs

    def form_valid(self, form):
        was_accepted = True if self.object.is_accepted() else False
        special_leave_b4_update = get_object_or_404(SpecialLeave, id=self.object.id)

        form.instance.status = SpecialLeave.PENDING_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()

        if was_accepted:
            signals.accepted_special_leave_updated.send(sender=SpecialLeave, instance=self.object)
        else:
            decisive_person_changed = form.instance.decisive_person != \
                                        special_leave_b4_update.decisive_person

            if decisive_person_changed:
                signals.special_leave_decisive_changed.send(sender=SpecialLeave,
                                                            instance=special_leave_b4_update)
                signals.special_leave_pending.send(sender=SpecialLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.can_update():
            return False

        return self.request.user == special_leave.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:special_leave_detail', kwargs={'pk': self.object.pk})


class SpecialLeaveDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_confirm_delete.html'
    success_url = '/'

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        signals.special_leave_deleted.send(sender=SpecialLeave, instance=self.object)
        
        return super(SpecialLeaveDeleteView, self).delete(*args, **kwargs)

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.can_delete():
            return False

        return self.request.user == special_leave.absent


class SpecialLeaveCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_confirm_cancel.html'
    fields = ['message_for_decisive_person',]

    def form_valid(self, form):
        form.instance.status = SpecialLeave.PENDING_TO_CANCEL_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.special_leave_pending_to_cancel.send(sender=SpecialLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.can_cancel():
            return False

        return self.request.user == special_leave.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:special_leave_detail', kwargs={'pk': self.object.pk})


class SpecialLeaveFinishEarlierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_finish_earlier.html'
    form_class = SpecialLeaveFinishEarlierForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['start_date'] = self.object.start_date
        kwargs['end_date'] = self.object.end_date
        
        return kwargs

    def form_valid(self, form):
        form.instance.status = SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.special_leave_pending_to_finish_earlier.send(sender=SpecialLeave, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.can_finish_earlier():
            return False

        return self.request.user == special_leave.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:special_leave_detail', kwargs={'pk': self.object.pk})


class SpecialLeavesModerationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leaves_moderation.html'
    context_object_name = 'special_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(SpecialLeavesModerationListView, self).get_context_data(**kwargs)
        vacation_leaves_to_moderate = VacationLeave.get_number_of_vacation_leaves_to_moderate(self.request.user)
        special_leaves_to_moderate = SpecialLeave.get_number_of_special_leaves_to_moderate(self.request.user)
        remote_works_to_moderate = RemoteWork.get_number_of_remote_works_to_moderate(self.request.user)
        context['vacation_leaves_to_moderate'] = '99+' if vacation_leaves_to_moderate > 99 \
                                                    else str(vacation_leaves_to_moderate)
        context['special_leaves_to_moderate'] = '99+' if special_leaves_to_moderate > 99 \
                                                    else str(special_leaves_to_moderate)
        context['remote_works_to_moderate'] = '99+' if remote_works_to_moderate > 99 \
                                                    else str(remote_works_to_moderate)
        return context

    def get_queryset(self):
        return SpecialLeave.objects.filter(status__in=(SpecialLeave.PENDING_STATUS,
                                            SpecialLeave.PENDING_TO_CANCEL_STATUS,
                                            SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS),
                                            decisive_person=self.request.user).order_by('-date_of_completion',
                                            '-start_date', '-end_date', 'absent')
    
    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class SpecialLeaveAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this special leave has already been made.'),}, status=200)

        colliding_absences_str = SpecialLeave.get_colliding_absences_info(special_leave.absent,
                                    special_leave.start_date, special_leave.end_date, special_leave.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        special_leave.status = SpecialLeave.ACCEPTED_STATUS
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(special_leave, _('Special leave was accepted.'))

        if context['ok']:
            signals.special_leave_accepted.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False
            
            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeaveRejectAjaxView(UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this special leave has already been made.'),}, status=200)

        special_leave.status = SpecialLeave.REJECTED_STATUS
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        special_leave.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(special_leave, _('Special leave was rejected.'))

        if context['ok']:
            signals.special_leave_rejected.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False
            
            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeaveAcceptCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this special leave cancelation has already been made.'),}, status=200)

        special_leave.status = SpecialLeave.CANCELED_STATUS
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(special_leave, _('Special leave cancelation was accepted.'))

        if context['ok']:
            signals.special_leave_canceled.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeaveRejectCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this special leave cancelation has already been made.'),}, status=200)

        if special_leave.confirming_person:
            special_leave.status = SpecialLeave.CONFIRMED_STATUS
        else:
            special_leave.status = SpecialLeave.ACCEPTED_STATUS
            
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            special_leave.rejection_reason = request.POST['reason']
        else:
            special_leave.rejection_reason = _('The request for cancelation was rejected.')

        context = get_leave_status_change_context(special_leave, _('Special leave cancelation was rejected.'))

        if context['ok']:
            signals.special_leave_cancelation_rejected.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class SpecialLeaveAcceptFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish special leave earlier has already been made.'),},
                status=200
                )

        if special_leave.confirming_person:
            special_leave.status = SpecialLeave.CONFIRMED_STATUS
        else:
            special_leave.status = SpecialLeave.ACCEPTED_STATUS
        
        special_leave.end_date = special_leave.pending_end_date
        special_leave.number_of_days = special_leave.pending_number_of_days
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(special_leave, 
                    _('Request to finish special leave earlier was accepted.'))

        if context['ok']:
            signals.special_leave_finished_earlier.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeaveRejectFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish vacation leave earlier has already been made.'),},
                status=200
                )
        
        if special_leave.confirming_person:
            special_leave.status = SpecialLeave.CONFIRMED_STATUS
        else:
            special_leave.status = SpecialLeave.ACCEPTED_STATUS
        
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            special_leave.rejection_reason = request.POST['reason']
        else:
            special_leave.rejection_reason = _('The request for special leave to finish earlier was rejected.')

        context = get_leave_status_change_context(special_leave,
                    _('Request to finish vacation leave earlier was rejected.'))

        if context['ok']:
            signals.special_leave_request_to_finish_earlier_rejected.send(
                sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class SpecialLeavesPreviouslyProcessedListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leaves_previously_processed.html'
    context_object_name = 'special_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(SpecialLeavesPreviouslyProcessedListView, self).get_context_data(**kwargs)
        context['status_choices'] = SpecialLeave.get_statuses()
        context['special_leave_reasons'] = SpecialLeaveReason.objects.all()

        return context
    
    def get_queryset(self):
        args = []
        kwargs = {}
        self.fill_query_args(args, kwargs)

        return SpecialLeave.objects.filter(decisive_person=self.request.user, *args, **kwargs
                            ).order_by('-date_of_completion', '-start_date','-end_date', 'absent')

    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            SpecialLeave.fill_query_args_absent_first_last_name(kwargs, 
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))

        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            SpecialLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            SpecialLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        statuses_without_filter = [SpecialLeave.ACCEPTED_STATUS, SpecialLeave.CONFIRMED_STATUS,
                                SpecialLeave.REJECTED_STATUS, SpecialLeave.CANCELED_BY_DECISIVE_STATUS,
                                SpecialLeave.CANCELED_STATUS,]

        if self.request.GET.get('leaveStatus', None) is not None:
            SpecialLeave.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(SpecialLeave.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('specialLeaveReason', None) is not None:
            SpecialLeave.fill_query_args_special_leave_reason(kwargs, self.request.GET['specialLeaveReason'])

        if len(self.request.GET.get('confirmativeFirstName', '')) > 0 or \
            len(self.request.GET.get('confirmativeLastName', '')) > 0:
            SpecialLeave.fill_query_args_confirmative_first_last_name(kwargs, 
                self.request.GET.get('confirmativeFirstName', ''), self.request.GET.get('confirmativeLastName', ''))

        if self.request.GET.get('specialLeaveId', None) is not None:
            SpecialLeave.fill_query_args_special_leave_id(kwargs, self.request.GET['specialLeaveId'])

    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class SpecialLeaveChangeDecisionAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this special leave can not be changed.'),}, status=200)

        if not special_leave.is_rejected():
            return JsonResponse({'ok': False, 'message': 
                _('This special leave is not rejected.'),}, status=200)

        colliding_absences_str = SpecialLeave.get_colliding_absences_info(special_leave.absent,
                                    special_leave.start_date, special_leave.end_date, special_leave.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        special_leave.status = SpecialLeave.ACCEPTED_STATUS
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(special_leave, _('Special leave was accepted.'))
        context['status_change_time'] = formats.date_format(special_leave.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.special_leave_decision_changed_accepted.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False
            
            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeaveChangeDecisionRejectAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        if not special_leave.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this special leave can not be changed.'),}, status=200)

        if not special_leave.is_accepted() and not special_leave.is_confirmed():
            return JsonResponse({'ok': False, 'message': 
                _('This special leave is not accepted.'),}, status=200)

        special_leave.status = SpecialLeave.CANCELED_BY_DECISIVE_STATUS
        special_leave.status_changed_by = request.user
        special_leave.last_status_change_time = general_functions.current_datetime()
        special_leave.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(special_leave, _('Special leave was rejected.'))
        context['status_change_time'] = formats.date_format(special_leave.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.special_leave_decision_changed_rejected.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)

    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if self.request.user == special_leave.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_special_leave'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False
            
            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class SpecialLeavesApplicationsListView(PermissionRequiredMixin, ListView):
    permission_required = 'absence_calendar.view_special_leave_document'
    model = SpecialLeave
    template_name = 'absence_calendar/special_leaves_applications.html'
    context_object_name = 'special_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(SpecialLeavesApplicationsListView, self).get_context_data(**kwargs)
        context['status_choices'] = SpecialLeave.get_statuses()
        context['special_leave_reasons'] = SpecialLeaveReason.objects.all()

        return context

    def get_queryset(self):
        kwargs = {}
        args = []
        self.fill_query_args(args, kwargs)

        order_args = []
        self.fill_order_args(order_args)

        return SpecialLeave.objects.filter(*args, **kwargs).order_by(*order_args)
    
    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            SpecialLeave.fill_query_args_absent_first_last_name(kwargs, 
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))

        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            SpecialLeave.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))

        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            SpecialLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            SpecialLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        if self.request.GET.get('lastStatusChangeDateStart', None) is not None:
            SpecialLeave.fill_query_args_last_status_change_time__gte(
                kwargs, self.request.GET['lastStatusChangeDateStart'] + ' 00:00')

        if self.request.GET.get('lastStatusChangeDateEnd', None) is not None:
            SpecialLeave.fill_query_args_last_status_change_time__lte(
                kwargs, self.request.GET['lastStatusChangeDateEnd'] + ' 23:59')

        statuses_without_filter = [SpecialLeave.ACCEPTED_STATUS, SpecialLeave.CONFIRMED_STATUS,
                                SpecialLeave.CANCELED_STATUS, SpecialLeave.CANCELED_BY_DECISIVE_STATUS,
                                SpecialLeave.PENDING_TO_CANCEL_STATUS, SpecialLeave.PENDING_STATUS,
                                SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS, SpecialLeave.REJECTED_STATUS,]

        if self.request.GET.get('leaveStatus', None) is not None:
            SpecialLeave.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(SpecialLeave.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('specialLeaveReason', None) is not None:
            SpecialLeave.fill_query_args_special_leave_reason(kwargs, self.request.GET['specialLeaveReason'])

        if len(self.request.GET.get('confirmativeFirstName', '')) > 0 or \
            len(self.request.GET.get('confirmativeLastName', '')) > 0:
                SpecialLeave.fill_query_args_confirmative_first_last_name(kwargs, 
                                self.request.GET.get('confirmativeFirstName', ''),
                                self.request.GET.get('confirmativeLastName', ''))

        if self.request.GET.get('specialLeaveId', None) is not None:
            SpecialLeave.fill_query_args_special_leave_id(kwargs, self.request.GET['specialLeaveId'])

    def fill_order_args(self, args):
        if self.request.GET.get('orderCol', None) is not None and \
            self.request.GET.get('orderDirection', None) is not None:
            order_column = self.request.GET['orderCol']
            order_direction = self.request.GET['orderDirection']
            direction_sign = ''

            if order_direction == 'desc':
                direction_sign = '-'
            
            if order_column == 'absent':
                args.append(direction_sign + 'absent__last_name')
                args.append(direction_sign + 'absent__first_name')
            elif order_column == 'decisive':
                args.append(direction_sign + 'decisive_person__last_name')
                args.append(direction_sign + 'decisive_person__first_name')
            elif order_column == 'leaveDateStart':
                args.append(direction_sign + 'start_date')
            elif order_column == 'leaveDateEnd':
                args.append(direction_sign + 'end_date')
            elif order_column == 'completionDate':
                args.append(direction_sign + 'date_of_completion')
            elif order_column == 'reason':
                args.append(direction_sign + 'reason')
            elif order_column == 'confirmative':
                args.append(direction_sign + 'confirming_person__last_name')
                args.append(direction_sign + 'confirming_person__first_name')
            elif order_column == 'lastStatusChangeDate':
                args.append(direction_sign + 'last_status_change_time')
        else:
            args.append(F('last_status_change_time').desc(nulls_first=True))
            args.append('-date_of_completion')
            args.append('-start_date')
            args.append('-end_date')
            args.append('absent')


class SpecialLeaveApplicationDetailView(UserPassesTestMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'absence_calendar.view_special_leave_document'
    model = SpecialLeave
    context_object_name = 'special_leave'
    template_name = 'absence_calendar/special_leave_application_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_name'] = global_live_settings.company.name
        context['city'] = global_live_settings.company.city

        return context

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.is_accepted() and not special_leave.is_confirmed() and \
            not special_leave.is_pending_to_cancel() and not special_leave.is_pending_to_finish_earlier():
            return False

        return True


@permission_required('absence_calendar.view_special_leave_document')
def special_leave_application_pdf(request, special_leave_id):
    special_leave = get_object_or_404(SpecialLeave, id=special_leave_id)
    
    if not special_leave.is_accepted() and not special_leave.is_confirmed() and \
        not special_leave.is_pending_to_cancel() and not special_leave.is_pending_to_finish_earlier():
            return HttpResponseForbidden()

    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {
        'special_leave': special_leave,
        'download_mode': True,
        'company_name': global_live_settings.company.name,
        'city': global_live_settings.company.city,
    }
    template_path = 'absence_calendar/special_leave_application_detail.html'
    filename = f'{_("Special leave")} - {special_leave_id}'
    
    return general_functions.get_pdf_response(options, context, template_path, filename)


@permission_required('absence_calendar.view_special_leave_document')
def special_leaves_applications_pdf(request):
    special_leaves = []

    if request.GET.get('id', None):
        for special_leave_id in request.GET.getlist('id'):
            special_leave = get_object_or_404(SpecialLeave, id=special_leave_id)

            if not special_leave.is_accepted() and not special_leave.is_confirmed() and \
                not special_leave.is_pending_to_cancel() \
                and not special_leave.is_pending_to_finish_earlier():
                return HttpResponseForbidden()

            special_leaves.append(special_leave)
    
    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {
        'special_leaves': special_leaves,
        'company_name': global_live_settings.company.name,
        'city': global_live_settings.company.city,
    }
    template_path = 'absence_calendar/special_leaves_applications_pdf.html'
    filename = _('Special leaves')

    return general_functions.get_pdf_response(options, context, template_path, filename)


class UserSpecialLeavesListView(LoginRequiredMixin, ListView):
    model = SpecialLeave
    template_name = 'absence_calendar/user_special_leaves.html'
    context_object_name = 'special_leaves'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(UserSpecialLeavesListView, self).get_context_data(**kwargs)
        context['status_choices'] = SpecialLeave.get_statuses()
        context['special_leave_reasons'] = SpecialLeaveReason.objects.all()
        context['sum_of_special_leave_days'] = 0

        for special_leave in context['special_leaves']:
            if special_leave.is_confirmed() or special_leave.is_accepted() or \
                special_leave.is_pending_to_finish_earlier() or special_leave.is_pending_to_cancel():
                context['sum_of_special_leave_days'] += special_leave.number_of_days

        return context

    def get_queryset(self):
        kwargs = self.get_query_args()

        return SpecialLeave.objects.filter(absent=self.request.user, **kwargs).order_by(
                            '-date_of_completion', '-start_date', '-end_date')

    def get_query_args(self):
        kwargs = {}

        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            SpecialLeave.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))

        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            SpecialLeave.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            SpecialLeave.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            SpecialLeave.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        if self.request.GET.get('leaveStatus', None) is not None:
            SpecialLeave.fill_query_args_status(kwargs, self.request.GET['leaveStatus'])

        if self.request.GET.get('specialLeaveReason', None) is not None:
            SpecialLeave.fill_query_args_special_leave_reason(kwargs, self.request.GET['specialLeaveReason'])

        if len(self.request.GET.get('confirmativeFirstName', '')) > 0 or \
            len(self.request.GET.get('confirmativeLastName', '')) > 0:
            SpecialLeave.fill_query_args_confirmative_first_last_name(kwargs, 
                self.request.GET.get('confirmativeFirstName', ''), self.request.GET.get('confirmativeLastName', ''))

        if self.request.GET.get('specialLeaveId', None) is not None:
            SpecialLeave.fill_query_args_special_leave_id(kwargs, self.request.GET['specialLeaveId'])

        return kwargs


class SpecialLeaveUpdateConfirmationDocumentData(UserPassesTestMixin, LoginRequiredMixin, UpdateView):
    model = SpecialLeave
    template_name = 'absence_calendar/special_leave_update_confirmation_document.html'
    form_class = SpecialLeaveUpdateConfirmationDocumentDataForm

    def test_func(self):
        special_leave = self.get_object()

        if not special_leave.can_update_document_confirmation_data():
            return False

        return self.request.user == special_leave.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:special_leave_detail', kwargs={'pk': self.object.pk})


class SpecialLeaveConfirmDocumentAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        special_leave = get_object_or_404(SpecialLeave, id=id)

        special_leave.status = SpecialLeave.CONFIRMED_STATUS
        special_leave.confirming_person = request.user
        context = get_leave_status_change_context(special_leave, _('Confirmation document was confirmed.'))
        context['username'] = request.user.profile.get_name()

        if context['ok']:
            signals.special_leave_confirmation_document_confirmed.send(sender=SpecialLeave, instance=special_leave)

        return JsonResponse(context, status=200)
    
    def test_func(self):
        special_leave = get_object_or_404(SpecialLeave, id=self.request.POST['id'])

        if not special_leave.can_confirm_document_data():
            return False

        if self.request.user == special_leave.decisive_person:
            return True
        
        if global_live_settings.absence_calendar.payroll_department_group is not None:
            if self.request.user.groups.filter(
                id=global_live_settings.absence_calendar.payroll_department_group.id).exists():
                return True

        return False

#######################################################################
# RemoteWork
#######################################################################


class RemoteWorkDetailView(UserPassesTestMixin, DetailView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_detail.html'

    def test_func(self):
        remote_work = self.get_object()

        if remote_work.is_accepted():
            return True
        else:
            return self.request.user == remote_work.absent or \
                self.request.user == remote_work.decisive_person


class RemoteWorkCreateView(LoginRequiredMixin, CreateView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_create.html'
    form_class = RemoteWorkCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_assessment_url'] = global_live_settings.absence_calendar.risk_assessment_url
        context['safety_rules_url'] = global_live_settings.absence_calendar.safety_rules_url
        context['personal_data_protection_url'] = global_live_settings.absence_calendar.personal_data_protection_url

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absent'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.absent = self.request.user
        print(form.instance.absent)
        self.object = form.save()
        signals.remote_work_pending.send(sender=RemoteWork, instance=self.object)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:remote_work_detail', kwargs={'pk': self.object.pk})


class RemoteWorkUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_update.html'
    form_class = RemoteWorkUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_assessment_url'] = global_live_settings.absence_calendar.risk_assessment_url
        context['safety_rules_url'] = global_live_settings.absence_calendar.safety_rules_url
        context['personal_data_protection_url'] = global_live_settings.absence_calendar.personal_data_protection_url

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['absence'] = self.object
        return kwargs

    def form_valid(self, form):
        was_accepted = True if self.object.is_accepted() else False
        remote_work_b4_update = get_object_or_404(RemoteWork, id=self.object.id)

        form.instance.status = RemoteWork.PENDING_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()

        if was_accepted:
            signals.accepted_remote_work_updated.send(sender=RemoteWork, instance=self.object)
        else:
            decisive_person_changed = form.instance.decisive_person != \
                                        remote_work_b4_update.decisive_person

            if decisive_person_changed:
                signals.remote_work_decisive_changed.send(sender=RemoteWork,
                                                            instance=remote_work_b4_update)
                signals.remote_work_pending.send(sender=RemoteWork, instance=self.object)
        
        return super().form_valid(form)

    def test_func(self):
        remote_work = self.get_object()

        if not remote_work.can_update():
            return False

        return self.request.user == remote_work.absent
    
    def get_success_url(self):
        return reverse_lazy('absence_calendar:remote_work_detail', kwargs={'pk': self.object.pk})


class RemoteWorkDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_confirm_delete.html'
    success_url = '/'

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        signals.remote_work_deleted.send(sender=RemoteWork, instance=self.object)
        
        return super(RemoteWorkDeleteView, self).delete(*args, **kwargs)

    def test_func(self):
        remote_work = self.get_object()

        if not remote_work.can_delete():
            return False

        return self.request.user == remote_work.absent


class RemoteWorkCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_confirm_cancel.html'
    fields = ['message_for_decisive_person',]

    def form_valid(self, form):
        form.instance.status = RemoteWork.PENDING_TO_CANCEL_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.remote_work_pending_to_cancel.send(sender=RemoteWork, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        remote_work = self.get_object()

        if not remote_work.can_cancel():
            return False

        return self.request.user == remote_work.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:remote_work_detail', kwargs={'pk': self.object.pk})


class RemoteWorkFinishEarlierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_finish_earlier.html'
    form_class = RemoteWorkFinishEarlierForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['start_date'] = self.object.start_date
        kwargs['end_date'] = self.object.end_date
        
        return kwargs

    def form_valid(self, form):
        form.instance.status = RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS
        form.instance.status_changed_by = self.request.user
        form.instance.last_status_change_time = general_functions.current_datetime()
        self.object = form.save()
        signals.remote_work_pending_to_finish_earlier.send(sender=RemoteWork, instance=self.object)
        
        return HttpResponseRedirect(self.get_success_url())

    def test_func(self):
        remote_work = self.get_object()

        if not remote_work.can_finish_earlier():
            return False

        return self.request.user == remote_work.absent

    def get_success_url(self):
        return reverse_lazy('absence_calendar:remote_work_detail', kwargs={'pk': self.object.pk})


class RemoteWorkModerationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_work_moderation.html'
    context_object_name = 'remote_works'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(RemoteWorkModerationListView, self).get_context_data(**kwargs)
        vacation_leaves_to_moderate = VacationLeave.get_number_of_vacation_leaves_to_moderate(self.request.user)
        special_leaves_to_moderate = SpecialLeave.get_number_of_special_leaves_to_moderate(self.request.user)
        remote_works_to_moderate = RemoteWork.get_number_of_remote_works_to_moderate(self.request.user)
        context['vacation_leaves_to_moderate'] = '99+' if vacation_leaves_to_moderate > 99 \
                                                    else str(vacation_leaves_to_moderate)
        context['special_leaves_to_moderate'] = '99+' if special_leaves_to_moderate > 99 \
                                                    else str(special_leaves_to_moderate)
        context['remote_works_to_moderate'] = '99+' if remote_works_to_moderate > 99 \
                                                    else str(remote_works_to_moderate)
        return context

    def get_queryset(self):
        return RemoteWork.objects.filter(status__in=(
                                                RemoteWork.PENDING_STATUS,
                                                RemoteWork.PENDING_TO_CANCEL_STATUS,
                                                RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS
                                            ),
                                            decisive_person=self.request.user).order_by('-date_of_completion',
                                            '-start_date', '-end_date', 'absent')

    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class RemoteWorkAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this remote work has already been made.'),}, status=200)

        colliding_absences_str = RemoteWork.get_colliding_absences_info(remote_work.absent,
                                    remote_work.start_date, remote_work.end_date, remote_work.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        remote_work.status = RemoteWork.ACCEPTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(remote_work, _('Remote work was accepted.'))

        if context['ok']:
            signals.remote_work_accepted.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class RemoteWorkRejectAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this remote work has already been made.'),}, status=200)

        remote_work.status = RemoteWork.REJECTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        remote_work.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(remote_work, _('Remote work was rejected.'))

        if context['ok']:
            signals.remote_work_rejected.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class RemoteWorkAcceptCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this remote work cancelation has already been made.'),}, status=200)

        remote_work.status = RemoteWork.CANCELED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(remote_work, _('Remote work cancelation was accepted.'))

        if context['ok']:
            signals.remote_work_canceled.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class RemoteWorkRejectCancelationAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending_to_cancel():
            return JsonResponse({'ok': False, 'message': 
                _('The decision on this remote work cancelation has already been made.'),}, status=200)

        remote_work.status = RemoteWork.ACCEPTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            remote_work.rejection_reason = request.POST['reason']
        else:
            remote_work.rejection_reason = _('The request for cancelation was rejected.')

        context = get_leave_status_change_context(remote_work, _('Remote work cancelation was rejected.'))

        if context['ok']:
            signals.remote_work_cancelation_rejected.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class RemoteWorkAcceptFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish remote work earlier has already been made.'),},
                status=200
                )

        remote_work.end_date = remote_work.pending_end_date
        remote_work.number_of_days = remote_work.pending_number_of_days
        remote_work.status = RemoteWork.ACCEPTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(remote_work,
                    _('Request to finish remote work earlier was accepted.'))

        if context['ok']:
            signals.remote_work_finished_earlier.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True

        return False


class RemoteWorkRejectFinishEarlierAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.is_pending_to_finish_earlier():
            return JsonResponse(
                {'ok': False, 'message': 
                _('The decision on this request to finish remote work earlier has already been made.'),},
                status=200
                )

        remote_work.status = RemoteWork.ACCEPTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()

        if request.POST['reason']:
            remote_work.rejection_reason = request.POST['reason']
        else:
            remote_work.rejection_reason = _('The request for remote work to finish earlier was rejected.')

        context = get_leave_status_change_context(remote_work,
                    _('Request to finish remote work earlier was rejected.'))

        if context['ok']:
            signals.remote_work_request_to_finish_earlier_rejected.send(
                sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True
            
            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class RemoteWorksPreviouslyProcessedListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = RemoteWork
    template_name = 'absence_calendar/remote_works_previously_processed.html'
    context_object_name = 'remote_works'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(RemoteWorksPreviouslyProcessedListView, self).get_context_data(**kwargs)
        context['status_choices'] = RemoteWork.get_statuses()

        return context

    def get_queryset(self):
        args = []
        kwargs = {}
        self.fill_query_args(args, kwargs)

        return RemoteWork.objects.filter(decisive_person=self.request.user, *args, **kwargs
                            ).order_by('-date_of_completion', '-start_date', '-end_date', 'absent')

    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            RemoteWork.fill_query_args_absent_first_last_name(kwargs,
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))
        
        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            RemoteWork.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            RemoteWork.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        statuses_without_filter = [RemoteWork.ACCEPTED_STATUS, RemoteWork.REJECTED_STATUS, 
                                    RemoteWork.CANCELED_BY_DECISIVE_STATUS, RemoteWork.CANCELED_STATUS,]

        if self.request.GET.get('leaveStatus', None) is not None:
            RemoteWork.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(RemoteWork.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('remoteWorkId', None) is not None:
            RemoteWork.fill_query_args_remote_work_id(kwargs, self.request.GET['remoteWorkId'])
    
    def test_func(self):
        if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
            return True

        try:
            employee = self.request.user.employee
        except Employee.DoesNotExist:
            return False

        return employee.is_manager() or employee.is_deputy_manager()


class RemoteWorkChangeDecisionAcceptAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this remote work can not be changed.'),}, status=200)

        if not remote_work.is_rejected():
            return JsonResponse({'ok': False, 'message': 
                _('This remote work is not rejected.'),}, status=200)

        colliding_absences_str = RemoteWork.get_colliding_absences_info(remote_work.absent,
                                    remote_work.start_date, remote_work.end_date, remote_work.id)

        if colliding_absences_str:
            return JsonResponse({
                'ok': False,
                'message': _('At the given date range employee is already absent!') + \
                    ' (' + colliding_absences_str + ')'
                }, status=200)

        remote_work.status = RemoteWork.ACCEPTED_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        context = get_leave_status_change_context(remote_work, _('Remote work was accepted.'))
        context['status_change_time'] = formats.date_format(remote_work.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.remote_work_decision_changed_accepted.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class RemoteWorkChangeDecisionRejectAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, id):
        remote_work = get_object_or_404(RemoteWork, id=id)

        if not remote_work.can_change_decision():
            return JsonResponse({'ok': False, 'message': 
                _('The decision regarding this remote work can not be changed.'),}, status=200)

        if not remote_work.is_accepted():
            return JsonResponse({'ok': False, 'message': 
                _('This remote work is not accepted.'),}, status=200)

        remote_work.status = RemoteWork.CANCELED_BY_DECISIVE_STATUS
        remote_work.status_changed_by = request.user
        remote_work.last_status_change_time = general_functions.current_datetime()
        remote_work.rejection_reason = request.POST['reason']
        context = get_leave_status_change_context(remote_work, _('Remote work was rejected.'))
        context['status_change_time'] = formats.date_format(remote_work.last_status_change_time,
                                                            'DATETIME_FORMAT')

        if context['ok']:
            signals.remote_work_decision_changed_rejected.send(sender=RemoteWork, instance=remote_work)

        return JsonResponse(context, status=200)

    def test_func(self):
        remote_work = get_object_or_404(RemoteWork, id=self.request.POST['id'])

        if self.request.user == remote_work.decisive_person:
            if self.request.user.has_perm('absence_calendar.moderate_remote_work'):
                return True

            try:
                employee = self.request.user.employee
            except Employee.DoesNotExist:
                return False

            if employee.is_manager() or employee.is_deputy_manager():
                return True
        
        return False


class RemoteWorksApplicationsListView(PermissionRequiredMixin, ListView):
    permission_required = 'absence_calendar.view_remote_work_document'
    model = RemoteWork
    template_name = 'absence_calendar/remote_works_applications.html'
    context_object_name = 'remote_works'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(RemoteWorksApplicationsListView, self).get_context_data(**kwargs)
        context['status_choices'] = RemoteWork.get_statuses()

        return context

    def get_queryset(self):
        kwargs = {}
        args = []
        self.fill_query_args(args, kwargs)

        order_args = []
        self.fill_order_args(order_args)

        return RemoteWork.objects.filter(*args, **kwargs).order_by(*order_args)
    
    def fill_query_args(self, args, kwargs):
        if self.request.GET.get('absentFirstName', None) is not None or \
            self.request.GET.get('absentLastName', None) is not None:
            RemoteWork.fill_query_args_absent_first_last_name(kwargs,
                self.request.GET.get('absentFirstName', ''), self.request.GET.get('absentLastName', ''))
            
        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            RemoteWork.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))
        
        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            RemoteWork.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            RemoteWork.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        if self.request.GET.get('lastStatusChangeDateStart', None) is not None:
            RemoteWork.fill_query_args_last_status_change_time__gte(
                kwargs, self.request.GET['lastStatusChangeDateStart'] + ' 00:00')

        if self.request.GET.get('lastStatusChangeDateEnd', None) is not None:
            RemoteWork.fill_query_args_last_status_change_time__lte(
                kwargs, self.request.GET['lastStatusChangeDateEnd'] + ' 23:59')

        statuses_without_filter = [RemoteWork.ACCEPTED_STATUS, RemoteWork.CANCELED_STATUS, 
                                    RemoteWork.CANCELED_BY_DECISIVE_STATUS, RemoteWork.PENDING_TO_CANCEL_STATUS,
                                    RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS, RemoteWork.PENDING_STATUS,
                                    RemoteWork.REJECTED_STATUS]

        if self.request.GET.get('leaveStatus', None) is not None:
            RemoteWork.fill_query_args_status_one_of(args, kwargs, self.request.GET['leaveStatus'], 
                                                        statuses_without_filter)
        else:
            args.append(RemoteWork.get_statuses_args(statuses_without_filter))

        if self.request.GET.get('remoteWorkId', None) is not None:
            RemoteWork.fill_query_args_remote_work_id(kwargs, self.request.GET['remoteWorkId'])

    def fill_order_args(self, args):
        if self.request.GET.get('orderCol', None) is not None and \
            self.request.GET.get('orderDirection', None) is not None:
            order_column = self.request.GET['orderCol']
            order_direction = self.request.GET['orderDirection']
            direction_sign = ''

            if order_direction == 'desc':
                direction_sign = '-'
            
            if order_column == 'absent':
                args.append(direction_sign + 'absent__last_name')
                args.append(direction_sign + 'absent__first_name')
            elif order_column == 'decisive':
                args.append(direction_sign + 'decisive_person__last_name')
                args.append(direction_sign + 'decisive_person__first_name')
            elif order_column == 'leaveDateStart':
                args.append(direction_sign + 'start_date')
            elif order_column == 'leaveDateEnd':
                args.append(direction_sign + 'end_date')
            elif order_column == 'completionDate':
                args.append(direction_sign + 'date_of_completion')
            elif order_column == 'lastStatusChangeDate':
                args.append(direction_sign + 'last_status_change_time')
        else:
            args.append(F('last_status_change_time').desc(nulls_first=True))
            args.append('-date_of_completion')
            args.append('-start_date')
            args.append('-end_date')
            args.append('absent')


class RemoteWorkApplicationDetailView(UserPassesTestMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'absence_calendar.view_remote_work_document'
    model = RemoteWork
    context_object_name = 'remote_work'
    template_name = 'absence_calendar/remote_work_application_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['city'] = global_live_settings.company.city

        return context

    def test_func(self):
        remote_work = self.get_object()

        if not remote_work.is_accepted() and not remote_work.is_pending_to_cancel() \
            and not remote_work.is_pending_to_finish_earlier():
            return False

        return True


@permission_required('absence_calendar.view_remote_work_document')
def remote_work_application_pdf(request, remote_work_id):
    remote_work = get_object_or_404(RemoteWork, id=remote_work_id)

    if not remote_work.is_accepted() and not remote_work.is_pending_to_cancel() \
        and not remote_work.is_pending_to_finish_earlier():
        return HttpResponseForbidden()

    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {
        'remote_work': remote_work,
        'download_mode': True,
        'city': global_live_settings.company.city,
    }
    template_path = 'absence_calendar/remote_work_application_detail.html'
    filename = f'{_("Remote work")} - {remote_work_id}'
    
    return general_functions.get_pdf_response(options, context, template_path, filename)


@permission_required('absence_calendar.view_remote_work_document')
def remote_works_applications_pdf(request):
    remote_works = []

    if request.GET.get('id', None):
        for remote_work_id in request.GET.getlist('id'):
            remote_work = get_object_or_404(RemoteWork, id=remote_work_id)

            if not remote_work.is_accepted() and not remote_work.is_pending_to_cancel() \
                and not remote_work.is_pending_to_finish_earlier():
                return HttpResponseForbidden()

            remote_works.append(remote_work)
    
    options = {
        'page-size': 'A4',
        'dpi': 400,
        'encoding': 'UTF-8',
        'quiet': '',
        'margin-top': '55px',
        'margin-right': '55px',
        'margin-bottom': '55px',
        'margin-left': '55px',
    }
    context = {'remote_works': remote_works, 'city': global_live_settings.company.city,}
    template_path = 'absence_calendar/remote_works_applications_pdf.html'
    filename = _('Remote works')

    return general_functions.get_pdf_response(options, context, template_path, filename)


class UserRemoteWorksListView(LoginRequiredMixin, ListView):
    model = RemoteWork
    template_name = 'absence_calendar/user_remote_works.html'
    context_object_name = 'remote_works'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(UserRemoteWorksListView, self).get_context_data(**kwargs)
        context['status_choices'] = RemoteWork.get_statuses()
        context['sum_of_remote_work_days'] = 0

        for remote_work in context['remote_works']:
            if remote_work.is_accepted() or remote_work.is_pending_to_cancel() or \
                remote_work.is_pending_to_finish_earlier():
                context['sum_of_remote_work_days'] += remote_work.number_of_days

        return context

    def get_queryset(self):
        kwargs = self.get_query_args()

        return RemoteWork.objects.filter(absent=self.request.user, **kwargs).order_by(
                                        '-date_of_completion', '-start_date', '-end_date')

    def get_query_args(self):
        kwargs = {}

        if self.request.GET.get('decisiveFirstName', None) is not None or \
            self.request.GET.get('decisiveLastName', None) is not None:
            RemoteWork.fill_query_args_decisive_first_last_name(kwargs, 
                self.request.GET.get('decisiveFirstName', ''), self.request.GET.get('decisiveLastName', ''))

        if self.request.GET.get('leaveRangeDateStart', None) is not None:
            RemoteWork.fill_query_args_end_date__gte(kwargs, self.request.GET['leaveRangeDateStart'])

        if self.request.GET.get('leaveRangeDateEnd', None) is not None:
            RemoteWork.fill_query_args_start_date__lte(kwargs, self.request.GET['leaveRangeDateEnd'])

        if self.request.GET.get('completionDateStart', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__gte(kwargs, self.request.GET['completionDateStart'])

        if self.request.GET.get('completionDateEnd', None) is not None:
            RemoteWork.fill_query_args_date_of_completion__lte(kwargs, self.request.GET['completionDateEnd'])

        if self.request.GET.get('leaveStatus', None) is not None:
            RemoteWork.fill_query_args_status(kwargs, self.request.GET['leaveStatus'])

        if self.request.GET.get('remoteWorkId', None) is not None:
            RemoteWork.fill_query_args_remote_work_id(kwargs, self.request.GET['remoteWorkId'])

        return kwargs


def absence_calendar(request, year, month):
    displayed_month = general_functions.validated_date(f'{year}-{month}-01')
    previous_month = displayed_month - timedelta(days=1)
    next_month = displayed_month + timedelta(days=monthrange(displayed_month.year, displayed_month.month)[1])

    days_data = get_days_data(previous_month, displayed_month, next_month)
    fill_days_data(days_data, previous_month, displayed_month, next_month)

    context = {
        'days': list(days_data.values()),
        'previous_date': {
            'year': previous_month.year,
            'month': previous_month.month,
        },
        'displayed_date': {
            'year': displayed_month.year,
            'month': displayed_month.month,
        },
        'next_date': {
            'year': next_month.year,
            'month': next_month.month,
        },
    }

    return render(request, 'absence_calendar/absence_calendar.html', context)


def get_days_data(previous_month, displayed_month, next_month):
    displayed_month_days_number = monthrange(displayed_month.year, displayed_month.month)[1]
    previous_month_days_number = monthrange(previous_month.year, previous_month.month)[1]
    first_weekday = datetime(displayed_month.year, displayed_month.month, 1).weekday()
    last_weekday = datetime(displayed_month.year, displayed_month.month, displayed_month_days_number).weekday()
    days_data = {}

    fill_month_leftovers_data(days_data, previous_month, previous_month_days_number-first_weekday+1, 
                                previous_month_days_number+1)
    fill_displayed_month_data(days_data, displayed_month, 1, displayed_month_days_number+1)
    fill_month_leftovers_data(days_data, next_month, 1, 7-last_weekday)

    return days_data


def fill_month_leftovers_data(days_data, month, day_start, day_end):
    for day_number in range(day_start, day_end):
        days_data[get_month_date_string(month, day_number)] = get_day_dict(day_number, False)


def fill_displayed_month_data(days_data, month, day_start, day_end):
    for day_number in range(day_start, day_end):
        day_dict = get_day_dict(day_number, True)

        if month.replace(day=day_number) == general_functions.current_date():
            day_dict['current_day'] = True

        days_data[get_month_date_string(month, day_number)] = day_dict


def get_day_dict(number, displayed_month):
    day_dict = {
        'number': number,
        'events': [],
        'vacation_leaves': [],
        'special_leaves': [],
        'absences': [],
        'remote_works': [],
    }

    if displayed_month:
        day_dict['displayed_month'] = True

    return day_dict


def get_month_date_string(month, day_number):
    return month.replace(day=day_number).strftime(settings.DATE_BACKEND_FORMAT)


def fill_days_data(days_data, previous_month, displayed_month, next_month):
    display_start_date = datetime.strptime(next(iter(days_data)), settings.DATE_BACKEND_FORMAT).date()
    display_end_date = datetime.strptime(next(reversed(days_data)), settings.DATE_BACKEND_FORMAT).date()

    fill_events(days_data, display_start_date, display_end_date)
    fill_vacation_leaves(days_data, display_start_date, display_end_date)
    fill_special_leaves(days_data, display_start_date, display_end_date)
    fill_absences(days_data, display_start_date, display_end_date)
    fill_remote_works(days_data, display_start_date, display_end_date)

    sort_days_data_by_absent_name(days_data)


def fill_events(days_data, display_start_date, display_end_date):
    events = Event.objects.filter(
        Q(date__gte=display_start_date) & Q(date__lte=display_end_date)).order_by('title')

    for event in events:
        event_data = get_event_data(event)
        append_event_data(days_data, event_data, event.date)


def get_event_data(event):
    event_data = {
        'id': event.id,
        'title': event.title,
    }

    return event_data


def append_event_data(days_data, event_data, date):
    days_data[date.strftime(settings.DATE_BACKEND_FORMAT)]['events'].append(event_data)


def fill_vacation_leaves(days_data, display_start_date, display_end_date):
    vacation_leaves = VacationLeave.objects.filter(status__in=(VacationLeave.ACCEPTED_STATUS,
        VacationLeave.PENDING_TO_CANCEL_STATUS, VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS)).exclude(
        Q(start_date__gt=display_end_date) | Q(end_date__lt=display_start_date)
        ).order_by('start_date', 'end_date')

    for vacation_leave in vacation_leaves:
        date_mark_start = general_functions.later_date(vacation_leave.start_date, display_start_date)
        date_mark_end = general_functions.earlier_date(vacation_leave.end_date, display_end_date)

        while date_mark_start <= date_mark_end:
            vacation_leave_data = get_vacation_leave_data(vacation_leave)
            append_vacation_leave_data(days_data, vacation_leave_data, date_mark_start)

            date_mark_start += timedelta(days=1)


def get_vacation_leave_data(vacation_leave):
    vacation_leave_data = {
        'id': vacation_leave.id,
        'absent_name': vacation_leave.absent.profile.get_name(),
    }

    return vacation_leave_data


def append_vacation_leave_data(days_data, vacation_leave_data, date):
    days_data[date.strftime(settings.DATE_BACKEND_FORMAT)]['vacation_leaves'].append(vacation_leave_data)


def fill_special_leaves(days_data, display_start_date, display_end_date):
    special_leaves = SpecialLeave.objects.filter(
            Q(status=SpecialLeave.ACCEPTED_STATUS) | Q(status=SpecialLeave.CONFIRMED_STATUS) | \
            Q(status=SpecialLeave.PENDING_TO_CANCEL_STATUS) | \
            Q(status=SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS)).exclude(
            Q(start_date__gt=display_end_date) | Q(end_date__lt=display_start_date)
        ).order_by('start_date', 'end_date')

    for special_leave in special_leaves:
        date_mark_start = general_functions.later_date(special_leave.start_date, display_start_date)
        date_mark_end = general_functions.earlier_date(special_leave.end_date, display_end_date)

        while date_mark_start <= date_mark_end:
            special_leave_data = get_special_leave_data(special_leave)
            append_special_leave_data(days_data, special_leave_data, date_mark_start)

            date_mark_start += timedelta(days=1)


def get_special_leave_data(special_leave):
    special_leave_data = {
        'id': special_leave.id,
        'absent_name': special_leave.absent.profile.get_name(),
    }

    return special_leave_data


def append_special_leave_data(days_data, special_leave_data, date):
    days_data[date.strftime(settings.DATE_BACKEND_FORMAT)]['special_leaves'].append(special_leave_data)


def fill_absences(days_data, display_start_date, display_end_date):
    absences = Absence.objects.exclude(Q(start_date__gt=display_end_date) | 
                Q(end_date__lt=display_start_date)).order_by('start_date', 'end_date',)
    
    for absence in absences:
        date_mark_start = general_functions.later_date(absence.start_date, display_start_date)
        date_mark_end = general_functions.earlier_date(absence.end_date, display_end_date)

        while date_mark_start <= date_mark_end:
            absence_data = get_absence_data(absence)
            append_absence_data_to_days_data(days_data, absence_data, date_mark_start)

            date_mark_start += timedelta(days=1)


def get_absence_data(absence):
    absence_data = {
        'id': absence.id,
        'absent_name': absence.absent.profile.get_name(),
        'absence_type': absence.absence_type.text,
    }

    return absence_data


def append_absence_data_to_days_data(days_data, absence_data, date):
    days_data[date.strftime(settings.DATE_BACKEND_FORMAT)]['absences'].append(absence_data)


def fill_remote_works(days_data, display_start_date, display_end_date):
    remote_works = RemoteWork.objects.filter(status__in=(RemoteWork.ACCEPTED_STATUS,
        RemoteWork.PENDING_TO_CANCEL_STATUS, RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS)).exclude(
        Q(start_date__gt=display_end_date) | Q(end_date__lt=display_start_date)
        ).order_by('start_date', 'end_date')

    for remote_work in remote_works:
        date_mark_start = general_functions.later_date(remote_work.start_date, display_start_date)
        date_mark_end = general_functions.earlier_date(remote_work.end_date, display_end_date)

        while date_mark_start <= date_mark_end:
            remote_work_data = get_remote_work_data(remote_work)
            append_remote_work_data(days_data, remote_work_data, date_mark_start)

            date_mark_start += timedelta(days=1)


def get_remote_work_data(remote_work):
    remote_work_data = {
        'id': remote_work.id,
        'absent_name': remote_work.absent.profile.get_name(),
    }

    return remote_work_data


def append_remote_work_data(days_data, remote_work_data, date):
    days_data[date.strftime(settings.DATE_BACKEND_FORMAT)]['remote_works'].append(remote_work_data)


def sort_days_data_by_absent_name(days_data):
    for day_data in days_data.values():
        sort_day_dict_by_absent_name(day_data['vacation_leaves'])
        sort_day_dict_by_absent_name(day_data['special_leaves'])
        sort_day_dict_by_absent_name(day_data['absences'])
        sort_day_dict_by_absent_name(day_data['remote_works'])


def sort_day_dict_by_absent_name(day_dict):
    day_dict.sort(key=lambda k: k['absent_name'])


def absence_calendar_day(request, year, month, day):
    displayed_day = general_functions.validated_date(f'{year}-{month}-{day}')
    context = get_absence_calendar_day_context(displayed_day)

    return render(request, 'absence_calendar/absence_calendar_day.html', context)


def get_absence_calendar_day_context(displayed_day):
    context = {
        'events': [],
        'vacation_leaves': [],
        'special_leaves': [],
        'absences': [],
        'remote_works': [],
        'displayed_day': displayed_day,
    }

    fill_day_context_with_events(context, displayed_day)
    fill_day_context_with_vacation_leaves(context, displayed_day)
    fill_day_context_with_special_leaves(context, displayed_day)
    fill_day_context_with_absences(context, displayed_day)
    fill_day_context_with_remote_works(context, displayed_day)
    
    previous_day = displayed_day - timedelta(days=1)
    next_day = displayed_day + timedelta(days=1)

    context['previous_day'] = {
        'year': previous_day.year,
        'month': previous_day.month,
        'day': previous_day.day,
    }
    context['next_day'] = {
        'year': next_day.year,
        'month': next_day.month,
        'day': next_day.day,
    }

    return context


def fill_day_context_with_events(context, displayed_day):
    events = Event.objects.filter(date=displayed_day).order_by('title')

    for event in events:
        context['events'].append(get_event_data(event))


def fill_day_context_with_vacation_leaves(context, day_date):
    vacation_leaves = VacationLeave.objects.filter(Q(start_date__lte=day_date) & Q(end_date__gte=day_date),
                        status__in=(VacationLeave.ACCEPTED_STATUS, VacationLeave.PENDING_TO_CANCEL_STATUS,
                                    VacationLeave.PENDING_TO_FINISH_EARLIER_STATUS))

    for vacation_leave in vacation_leaves:
        context['vacation_leaves'].append(get_vacation_leave_data(vacation_leave))
    
    sort_day_dict_by_absent_name(context['vacation_leaves'])


def fill_day_context_with_special_leaves(context, day_date):
    special_leaves = SpecialLeave.objects.filter(Q(start_date__lte=day_date) & Q(end_date__gte=day_date),
                        status__in=(SpecialLeave.ACCEPTED_STATUS, SpecialLeave.CONFIRMED_STATUS,
                                    SpecialLeave.PENDING_TO_CANCEL_STATUS,
                                    SpecialLeave.PENDING_TO_FINISH_EARLIER_STATUS))

    for special_leave in special_leaves:
        context['special_leaves'].append(get_special_leave_data(special_leave))

    sort_day_dict_by_absent_name(context['special_leaves'])


def fill_day_context_with_absences(context, day_date):
    absences = Absence.objects.filter(Q(start_date__lte=day_date) & Q(end_date__gte=day_date))

    for absence in absences:
        absence_data = get_absence_data(absence)
        context['absences'].append(absence_data)

    sort_day_dict_by_absent_name(context['absences'])


def fill_day_context_with_remote_works(context, day_date):
    remote_works = RemoteWork.objects.filter(Q(start_date__lte=day_date) & Q(end_date__gte=day_date),
                        status__in=(RemoteWork.ACCEPTED_STATUS, RemoteWork.PENDING_TO_CANCEL_STATUS,
                                    RemoteWork.PENDING_TO_FINISH_EARLIER_STATUS))

    for remote_work in remote_works:
        context['remote_works'].append(get_remote_work_data(remote_work))
    
    sort_day_dict_by_absent_name(context['remote_works'])


def get_leave_status_change_context(leave, message):
    try:
        leave.full_clean()
        leave.save()
        response_message = message
        response_state = True
    except ValidationError as e:
        response_message = general_functions.get_error_message(e, _('A validation error occured.'))
        response_state = False

    context = {
        'ok': response_state,
        'message': response_message,
    }

    return context
