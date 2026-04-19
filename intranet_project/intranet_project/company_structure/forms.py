from django import forms
from .models import Employee


class EmployeeFillAdditionalDataForm(forms.ModelForm):

    class Meta:
        model = Employee
        fields = ['region_name', 'region_code', 'cities',]
