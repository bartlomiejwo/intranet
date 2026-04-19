from django.contrib import admin
from .models import JobLog
from django.utils.translation import gettext_lazy as _


class JobLogAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'log_status', 'log_time', 'description']
    ordering = ['-log_time', 'job_id',]
    search_fields = ['job_id', 'log_status', 'log_time',]

admin.site.register(JobLog, JobLogAdmin)
