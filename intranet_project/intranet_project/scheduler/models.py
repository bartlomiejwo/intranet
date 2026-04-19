from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.urls import reverse
import notifier


class JobLog(models.Model):
    class Meta:
        verbose_name = _('job log')
        verbose_name_plural = _('job logs')

    job_id = models.CharField(max_length=100, verbose_name=_('job id'))
    log_status = models.CharField(max_length=25, verbose_name=_('log status'))
    log_time = models.DateTimeField(default=timezone.now, verbose_name=_('log time'))
    description = models.TextField(verbose_name=_('description'))

    @staticmethod
    def info(job_id, description):
        status = 'INFO'
        JobLog.objects.create(job_id=job_id, log_status=status, description=description)

    @staticmethod
    def exception(job_id, description):
        status = 'EXCEPTION'
        JobLog.objects.create(job_id=job_id, log_status=status, description=description)

        JobLog.notify_admins(job_id, status)

    @staticmethod
    def warning(job_id, description):
        status = 'WARNING'
        JobLog.objects.create(job_id=job_id, log_status=status, description=description)

        JobLog.notify_admins(job_id, status)

    @staticmethod
    def error(job_id, description):
        status = 'ERROR'
        JobLog.objects.create(job_id=job_id, log_status=status, description=description)

        JobLog.notify_admins(job_id, status)

    @staticmethod
    def notify_admins(job_id, status):
        admins = User.objects.filter(is_superuser=True, is_active=True)
        title = _('Scheduled job encountered problems')
        description = _('Scheduled job %(job_id)s has encountered problems (status=%(problem_status)s).') \
            % {'job_id': job_id, 'problem_status': status,}
        redirect_url = reverse('admin:scheduler_joblog_changelist')

        for admin in admins:
            if admin.profile.job_scheduler_app_notifications:
                notifier.models.Notification.objects.create(receiver=admin, title=title, 
                                        description=description, redirect_url=redirect_url)

            if admin.profile.job_scheduler_email_notifications:
                if admin.email:
                    notifier.email_thread.send_html_mail(title, description, [admin.email,])

    def __str__(self):
        return f'{self.job_id} {self.log_time}'
