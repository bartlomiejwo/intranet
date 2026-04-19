from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('profile/<int:pk>/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/<int:pk>/update_avatar/', views.ProfileAvatarUpdateView.as_view(), name='profile_avatar_update'),
    path('profile/<int:pk>/update_notifications/', views.ProfileNotificationsUpdateView.as_view(),
        name='profile_notifications_update'),
]
