from django.urls import path
from . import views

app_name = 'custom_pages'

urlpatterns = [
    path('<slug:page_url>/', views.dynamic_page_view, name='page'),
]
