"""intranet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView


favicon_view = RedirectView.as_view(
    url=settings.LIVE_SETTINGS_ACTIVE_LOGO_URL,
    permanent=True
)

urlpatterns = [
    path('favicon.ico', favicon_view),
    path('tinymce/', include('tinymce.urls')),
    path('admin/', admin.site.urls),
    path('', include('intranet.urls')),
    path('users/', include('users.urls')),
    path('pages/', include('custom_pages.urls')),
    path('rooms/', include('conference_rooms.urls')),
    path('absence_calendar/', include('absence_calendar.urls')),
    path('company_structure/', include('company_structure.urls')),
    path('files_management/', include('files_management.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
