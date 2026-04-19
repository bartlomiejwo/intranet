from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext


class Notification(models.Model):
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')

    receiver = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('receiver'))
    redirect_url = models.SlugField(verbose_name=_('redirect url'))
    title = models.CharField(max_length=100, null=False, blank=False,
                            verbose_name=pgettext('title', 'the name of something'))
    description = models.TextField(null=False, blank=False, verbose_name=_('description'))
    date_created = models.DateTimeField(default=timezone.now, verbose_name=_('date created'))
    checked = models.BooleanField(default=False, verbose_name=_('checked'))

    def __str__(self):
        return self.title
