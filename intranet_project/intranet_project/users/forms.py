from django import forms
from .models import Profile


class ProfileAvatarUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image',]


class ProfileNotificationsUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['app_notifications', 'email_notifications']
