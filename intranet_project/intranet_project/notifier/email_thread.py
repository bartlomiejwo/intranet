import threading
from django.core.mail import EmailMessage
from django.conf import settings
from live_settings.global_live_settings import global_live_settings
from django.template.loader import render_to_string
import msal
import requests


class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list, attachments=None):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        
        if attachments:
            self.attachments = attachments

        threading.Thread.__init__(self)

    def run (self):
        # msg = EmailMessage(self.subject, self.html_content, settings.EMAIL_HOST_USER, self.recipient_list)
        # msg.content_subtype = 'html'
        # msg.send()
        graph_token = get_graph_token(settings.GRAPH_CLIENT_ID, settings.GRAPH_CLIENT_SECRET, settings.GRAPH_TENANT_ID)
        
        if graph_token:
            send_mail_via_graph(graph_token, settings.GRAPH_SENDER, self.recipient_list, self.subject, self.html_content)


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


def get_graph_token(client_id, client_secret, tenant_id):
    graph_scope = ["https://graph.microsoft.com/.default"]
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f"https://login.microsoftonline.com/{tenant_id}"
    )
    result = app.acquire_token_for_client(scopes=graph_scope)
    if "access_token" not in result:
        raise Exception(f"Couldn't download token: {result.get('error_description')}")
    return result["access_token"]


def send_mail_via_graph(access_token, sender_email, receiver_emails, subject, body_text):
    graph_endpoint = "https://graph.microsoft.com/v1.0"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    to_recipients = [{"emailAddress": {"address": email}} for email in receiver_emails]

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_text},
            "toRecipients": to_recipients,
        },
        "saveToSentItems": "false"
    }

    response = requests.post(
        f"{graph_endpoint}/users/{sender_email}/sendMail",
        headers=headers,
        json=message
    )

    # if not response.ok:
    #     raise Exception(f"Error sending email ({response.status_code}): {response.text}")



