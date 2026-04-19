from django.contrib import admin
from .models import Post, Comment, Like
from live_settings.global_live_settings import global_live_settings


class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'date_created']
    search_fields = ['author__username', 'author__first_name', 'author__last_name',]


class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'date_posted']
    list_filter = ['date_posted']
    search_fields = ['post__title', 'author__username', 'author__first_name', 'author__last_name',]


class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'timestamp', 'post', 'comment']
    search_fields = ['user__username', 'user__first_name', 'user__last_name',]

admin.site.site_header = global_live_settings.general.admin_website_name

admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Like, LikeAdmin)