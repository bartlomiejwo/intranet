from django.contrib import admin
from .models import IntranetFile


class IntranetFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'file', 'file_size', 'upload_date', 'usage_counter', 'added_with_wysiwyg',]
    search_fields = ['name', 'owner__username', 'owner__first_name', 'owner__last_name',]


admin.site.register(IntranetFile, IntranetFileAdmin)