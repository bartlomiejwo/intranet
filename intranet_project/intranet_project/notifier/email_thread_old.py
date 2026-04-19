import threading
from django.core.mail import EmailMessage
from django.conf import settings
from live_settings.global_live_settings import global_live_settings
from django.template.loader import render_to_string


class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list, attachments=None):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        
        if attachments:
            self.attachments = attachments

        threading.Thread.__init__(self)

    def run (self):
        msg = EmailMessage(self.subject, self.html_content, settings.EMAIL_HOST_USER, self.recipient_list)
        msg.content_subtype = 'html'
        msg.send()


def send_html_mail(subject, html_content, recipient_list):
    email_subject = (f'{global_live_settings.notifier.email_subject_prefix} {str(subject)} '
                    f'{global_live_settings.notifier.email_subject_suffix}')
    template_path = 'notifier/email_notification.html'
    context = {
        'email_title': str(subject),
        'section_title': str(subject),
        'content_text': html_content,
        'footer_text': global_live_settings.notifier.email_footer,
    }
    content = render_to_string(template_path, context)

    EmailThread(email_subject, content, recipient_list).start()
