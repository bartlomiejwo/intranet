from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy

from .forms import ProfileAvatarUpdateForm, ProfileNotificationsUpdateForm
from .models import Profile
from live_settings.global_live_settings import global_live_settings


class ProfileDetailView(DetailView):
    model = Profile
    template_name = 'users/profile_detail.html'

    def get_context_data(self, **kwargs):
        data = super(ProfileDetailView, self).get_context_data(**kwargs)
        data['request_user_is_in_payroll_department'] = self.request.user.groups.filter(
                id=global_live_settings.absence_calendar.payroll_department_group.id).exists()

        return data


class ProfileAvatarUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    template_name = 'users/profile_avatar_update.html'
    form_class = ProfileAvatarUpdateForm

    def test_func(self):
        profile = self.get_object()

        return self.request.user == profile.user
    
    def get_success_url(self):
        return reverse_lazy('users:profile_detail', kwargs={'pk': self.object.pk})


class ProfileNotificationsUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    template_name = 'users/profile_notifications_update.html'
    form_class = ProfileNotificationsUpdateForm

    def test_func(self):
        profile = self.get_object()

        return self.request.user == profile.user
    
    def get_success_url(self):
        return reverse_lazy('users:profile_detail', kwargs={'pk': self.object.pk})

