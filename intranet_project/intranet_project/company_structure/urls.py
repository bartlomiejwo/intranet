from django.urls import path
from . import views


app_name = 'company_structure'

urlpatterns = [
    path('employees/', views.EmployeesListView.as_view(), name='employees'),
    path('employees/vcf/', views.generate_contacts_vcf, name='generate_vcf'),
    path('employees/csv/', views.generate_contacts_csv, name='generate_csv'),
    path('employee/<int:pk>/fill_additional_data/', views.EmployeeFillAdditionalDataView.as_view(),
        name='fill_employee_additional_data'),
]
