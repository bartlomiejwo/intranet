from django.contrib import admin
from .models import Department, SubordinateDepartment, Employee, DepartmentMember


class SubordinateDepartmentInLine(admin.StackedInline):
    model = SubordinateDepartment
    fk_name = 'parent_department'
    extra = 1



class DepartmentMemberInLineDepartment(admin.StackedInline):
    model = DepartmentMember
    fk_name = 'department'
    extra = 1


class DepartmentAdmin(admin.ModelAdmin):
    inlines = [SubordinateDepartmentInLine, DepartmentMemberInLineDepartment]
    list_display = ['name', ]
    search_fields = ['name',]


class DepartmentMemberInLineEmployee(admin.StackedInline):
    model = DepartmentMember
    fk_name = 'employee'
    extra = 1


class EmployeeAdmin(admin.ModelAdmin):
    inlines = [DepartmentMemberInLineEmployee,]
    list_display = ['user', ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name']


admin.site.register(Department, DepartmentAdmin)
admin.site.register(Employee, EmployeeAdmin)
