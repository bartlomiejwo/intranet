from django.contrib import admin
from .models import Notification

class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'receiver', 'date_created']
    ordering = ['-date_created', 'receiver', 'title']
    search_fields = ['receiver__username', 'receiver__first_name', 'receiver__last_name',]

admin.site.register(Notification, NotificationAdmin)
