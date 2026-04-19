from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from PIL import Image

from intranet_project import general_functions
import files_management.models as files_management_models
from notifier.models import Notification


class Profile(models.Model):
    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('user'))
    image = models.ImageField(upload_to=files_management_models.get_file_path, null=True, blank=True,
                                help_text=_('Provide 50x50 image in PNG format.'), verbose_name=_('image'))
    files_capacity_limit = models.PositiveIntegerField(default=1, 
                                help_text=_('Files capacity limit in megabytes.'), 
                                verbose_name=_('files capacity limit'))
    
    app_notifications = models.BooleanField(default=True, verbose_name=_('app notifications'))
    email_notifications = models.BooleanField(default=True, verbose_name=_('email notifications'))

    job_scheduler_app_notifications = models.BooleanField(default=False,
                                                    verbose_name=_('job scheduler app notifications'))
    job_scheduler_email_notifications = models.BooleanField(default=False,
                                                    verbose_name=_('job scheduler email notifications'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            image = Image.open(self.image.path)
            output_size = (50, 50)
            image.thumbnail(output_size)
            image.save(self.image.path)

    def get_name(self):
        if self.user.first_name or self.user.last_name:
            return self.user.first_name + ' ' + self.user.last_name
            
        return self.user.username

    def get_name_reversed(self):
        if self.user.first_name or self.user.last_name:
            return self.user.last_name + ' ' + self.user.first_name
            
        return self.user.username
    
    def get_files_capacity_usage(self):
        usage = files_management_models.IntranetFile.get_user_files_capacity_usage(self.user)

        return general_functions.get_human_readable_file_size(usage)

    def get_notifications(self):
        return list(Notification.objects.filter(receiver=self.user).order_by('-date_created')[:99])

    def __str__(self):
        return f'{self.user.username} profile'
