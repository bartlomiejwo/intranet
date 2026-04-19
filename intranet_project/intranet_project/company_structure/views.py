import tempfile

from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, UpdateView
from django.db import transaction
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import Employee, Department, DepartmentMember
from live_settings.global_live_settings import global_live_settings
from .forms import EmployeeFillAdditionalDataForm


class EmployeeFillAdditionalDataView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = 'company_structure.can_fill_employee_additional_data'
    model = Employee
    template_name = 'company_structure/employee_fill_additional_data.html'
    form_class = EmployeeFillAdditionalDataForm

    def get_success_url(self):
        return reverse_lazy('users:profile_detail', kwargs={'pk': self.object.user.profile.pk})


class EmployeesListView(ListView):
    model = Employee
    template_name = 'company_structure/employees.html'
    context_object_name = 'employees'
    paginate_by = 50

    def get_context_data(self,**kwargs):
        context = super(EmployeesListView, self).get_context_data(**kwargs)
        context['departments_list'] = Department.objects.all().order_by('name')
        context['selected_departments'] = self.request.GET.getlist('dep')

        return context

    def get_queryset(self):
        return get_employees_list_queryset(self.request)


def generate_contacts_vcf(request):
    employees = get_employees_list_queryset(request)
    encoding = 'utf-8'
    f = tempfile.TemporaryFile()

    write_vcf_contacts(employees, f, encoding)
    f.seek(0)

    response = HttpResponse(f.read(), content_type='text/x-vcard', charset=encoding)
    response['Content-Disposition'] = f'inline; filename=emp_' + \
        f'{timezone.localtime(timezone.now()).strftime("%Y_%m_%d_%H_%M_%S")}.vcf'

    f.close()
    
    return response


def generate_contacts_csv(request):
    employees = get_employees_list_queryset(request)
    encoding = 'windows-1250'
    f = tempfile.TemporaryFile()

    write_csv_contacts(employees, f, encoding)
    f.seek(0)

    response = HttpResponse(f.read(), content_type='text/csv', charset=encoding)
    response['Content-Disposition'] = f'inline; filename=emp_' + \
        f'{timezone.localtime(timezone.now()).strftime("%Y_%m_%d_%H_%M_%S")}.csv'

    f.close()
    
    return response


def get_employees_list_queryset(request):
    kwargs = {}
    args = []

    fill_employees_list_query_args(request, args, kwargs)

    employees = Employee.objects.filter(*args, **kwargs).order_by('user__last_name', 'user__first_name')

    with transaction.atomic():
        for employee in employees:
            employee.v_department_name = employee.get_department_name()
            employee.v_section_name = employee.get_section()

    employees = filter_employees_list_after_db_query(employees, request)
    employees = sort_employees_list(employees, request)
    
    return employees


def fill_employees_list_query_args(request, args, kwargs):
    kwargs['user__is_active'] = True

    if request.GET.get('employeeFirstName', None) is not None or \
        request.GET.get('employeeLastName', None) is not None:
        kwargs['user__first_name__icontains'] = request.GET.get('employeeFirstName', '')
        kwargs['user__last_name__icontains'] = request.GET.get('employeeLastName', '')
    
    if request.GET.get('title', None) is not None:
        kwargs['title__icontains'] = request.GET.get('title')

    if request.GET.get('regionName', None) is not None:
        kwargs['region_name__icontains'] = request.GET.get('regionName')

    if request.GET.get('regionCode', None) is not None:
        kwargs['region_code__icontains'] = request.GET.get('regionCode')

    if request.GET.get('city', None) is not None:
        kwargs['cities__icontains'] = request.GET.get('city')
    
    if request.GET.get('phone', None) is not None:
        Employee.fill_query_search_args_phone(args, request.GET.get('phone'))

    if request.GET.get('location', None) is not None:
        kwargs['location__icontains'] = request.GET.get('location')

    if request.GET.getlist('dep', None) is not None:
        if len(request.GET.getlist('dep')):
            employees_in_chosen_departments = []

            for department_id in request.GET.getlist('dep'):
                try:
                    department_id = int(department_id)
                except ValueError:
                    pass
                else:
                    employees_in_chosen_departments += \
                        Department.get_employee_ids_who_are_members_of_department(department_id)

            if 'id__in' in kwargs:
                kwargs['id__in'] += employees_in_chosen_departments
            else:
                kwargs['id__in'] = employees_in_chosen_departments


def filter_employees_list_after_db_query(employees_to_filter, request):
    if request.GET.get('companySection', None) is not None:
        company_section = request.GET.get('companySection').lower()
        
        if company_section:
            employees_to_filter = \
                [x for x in employees_to_filter if company_section in x.v_section_name.lower()]
        
    return employees_to_filter


def sort_employees_list(employees, request):
    if request.GET.get('orderCol', None) is not None and \
        request.GET.get('orderDirection', None) is not None:
        order_column = request.GET['orderCol']
        order_direction = request.GET['orderDirection']
        descending = False if order_direction == 'asc' else True

        if order_column == 'section':
            return sorted(employees, key=lambda x: x.v_section_name, reverse=descending)
        elif order_column == 'department':
            return sorted(employees, key=lambda x: x.v_department_name, reverse=descending)
        elif order_column == 'employee':
            return sorted(employees, key=lambda x: (x.user.last_name, x.user.first_name), reverse=descending)
        elif order_column == 'title':
            return sorted(employees, key=lambda x: x.title, reverse=descending)
        elif order_column == 'email':
            return sorted(employees, key=lambda x: x.user.email, reverse=descending)
        elif order_column == 'regionCode':
            return sorted(employees, key=lambda x: x.region_code, reverse=descending)

    return sorted(employees, key=lambda x: x.v_department_name)


def write_vcf_contacts(employees, f, encoding):
    vencoding = f'ENCODING=quoted-printable;CHARSET={encoding}'

    for employee in employees:
        if employee.cell_phone_number or employee.internal_phone_number or \
            employee.additional_phone_number:
            f.write(b'BEGIN:VCARD\n')
            f.write(b'VERSION:3.0\n')
            f.write(f'N;{vencoding}:{employee.user.last_name};{employee.user.first_name}\n'.encode(encoding))
            f.write(f'FN;{vencoding}:{employee.user.profile.get_name()}\n'.encode(encoding))
            f.write((f'ORG;{vencoding}:{global_live_settings.company.name};' + \
                f'{employee.get_department_name()}\n').encode(encoding))
            f.write(f'TITLE;{vencoding}:{employee.title}\n'.encode(encoding))
            f.write(f'EMAIL:{employee.user.email}\n'.encode(encoding))
            f.write(f'TEL;CELL:{employee.cell_phone_number}\n'.encode(encoding))
            f.write(f'TEL;CELL:{employee.short_cell_phone_number}\n'.encode(encoding))
            f.write(f'TEL;WORK:{employee.internal_phone_number}\n'.encode(encoding))
            f.write(f'TEL;WORK:{employee.additional_phone_number}\n'.encode(encoding))
            f.write((f'NOTE;{vencoding}:{employee.region_name};{employee.region_code};' + \
                f'{employee.cities}\n').encode(encoding))
            f.write(b'END:VCARD\n')


def write_csv_contacts(employees, f, encoding):
    f.write(('"Tytuł","Imię","Drugie imię","Nazwisko","Sufiks","Firma","Dział","Stanowisko"' + \
            ',"Adres służbowy - ulica","Adres służbowy - ulica 2","Adres służbowy - ulica 3","A' + \
            'dres służbowy - miejscowość","Adres służbowy - województwo","Adres służbowy - kod ' + \
            '"pocztowy","Adres służbowy - kraj","Adres domowy - ulica","Adres domowy - ulica (2)' + \
            '","Adres domowy - ulica (3)","Adres domowy - miejscowość","Adres domowy - województwo",' + \
            '"Adres domowy - kod pocztowy","Adres domowy - kraj","Inny adres - ulica","Inny adres - ' + \
            'ulica 2","Inny adres - ulica 3","Inny adres - miejscowość","Inny adres - województwo","' + \
            'Inny adres - kod pocztowy","Inny adres - kraj","Telefon asystenta","Faks służbowy","Telefon' + \
            ' służbowy","Telefon służbowy 2","Wywołanie zwrotne","Telefon w samochodzie","Główny' + \
            ' telefon do firmy","Faks domowy","Telefon domowy","Telefon domowy 2","ISDN","Telefon' + \
            ' komórkowy","Inny faks","Inny telefon","Pager","Telefon podstawowy","Radiotelefon","Te' + \
            ' lefon TTY/TDD","Teleks","Adres e-mail","Typ e-mail","Wyświetlana nazwa e-mail","Adres ' + \
            'e-mail 2","Rodzaj e-mail 2","Wyświetlana nazwa e-mail 2","Adres e-mail 3","Rodzaj e-mail 3"' + \
            ',"Wyświetlana nazwa e-mail 3","Charakter","Domowa skrzynka pocztowa","Dzieci","Hobby","Imię i' + \
            ' nazwisko asystenta","Informacje rozliczeniowe","Inicjały","Inna skrzynka pocztowa","Int' + \
            'ernetowe informacje wolny/zajęty","Język","Kategorie","Konto","Lokalizacja","Lokalizacja b' + \
            'iura","Menedżer","Notatki","Numer ewidencyjny w organizacji","Osoba polecająca","PESEL","Pł' + \
            'eć","Priorytet","Prywatne","Przebieg","Rocznica","Serwer adresowy","Słowa kluczowe","Służbowa' + \
            ' skrzynka pocztowa","Strona sieci Web","Urodziny","Użytkownik 1","Użytkownik 2","Użytkownik ' + \
            '3","Użytkownik 4","Współmałżonek","Zawód"\r\n').encode(encoding))
    
    for employee in employees:
        f.write((f'"","{employee.user.first_name}","","{employee.user.last_name}","","' + \
                f'{global_live_settings.company.name}","{employee.get_department_name()}' + \
                f'","{employee.title}",,,,,,,,,,,,,,,,,,,,,,,,"{employee.internal_phone_number}' + \
                f'","",,,,,,,,"{employee.cell_phone_number}",,"{employee.additional_phone_number}' + \
                f'",,,,,,"{employee.user.email}","SMTP","{employee.user.first_name} ' + \
                f'{employee.user.last_name} ({employee.user.email})",,,,,,,"",,,,,,,,,"","' + \
                f'{global_live_settings.company.name}","","",,,"{employee.region_name};' + \
                f'{employee.region_code};{employee.cities}",,,,"","","",,"",,"",,,""\r\n').encode(encoding))
