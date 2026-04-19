from django.contrib import admin
from .models import GlpiDepartment, GlpiSubordinateDepartment, GlpiEmployee, GlpiDepartmentMember


class SubordinateGlpiDepartmentInLine(admin.StackedInline):
    model = GlpiSubordinateDepartment
    fk_name = 'glpi_parent_department'
    extra = 1


class GlpiDepartmentMemberInLineGlpiDepartment(admin.StackedInline):
    model = GlpiDepartmentMember
    fk_name = 'glpi_department'
    extra = 1


class GlpiDepartmentAdmin(admin.ModelAdmin):
    inlines = [SubordinateGlpiDepartmentInLine, GlpiDepartmentMemberInLineGlpiDepartment]
    search_fields = ['department__name',]


class GlpiDepartmentMemberInLineGlpiEmployee(admin.StackedInline):
    model = GlpiDepartmentMember
    fk_name = 'glpi_employee'
    extra = 1


class GlpiEmployeeAdmin(admin.ModelAdmin):
    inlines = [GlpiDepartmentMemberInLineGlpiEmployee,]
    search_fields = ['employee__user__username', 'employee__user__first_name', 'employee__user__last_name']


admin.site.register(GlpiDepartment, GlpiDepartmentAdmin)
admin.site.register(GlpiEmployee, GlpiEmployeeAdmin)
