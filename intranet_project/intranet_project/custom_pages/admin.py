from django.contrib import admin
from custom_pages.models import Tab, Page


class PageAdmin(admin.ModelAdmin):
    list_display = ['title', 'parent_tab', 'position']
    ordering = ['parent_tab', 'position',]


class TabAdmin(admin.ModelAdmin):
    list_display = ['title', 'position',]
    ordering = ['position', 'title']


admin.site.register(Tab, TabAdmin)
admin.site.register(Page, PageAdmin)
