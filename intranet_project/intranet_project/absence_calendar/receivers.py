import os
import uuid
from pathlib import Path

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.template.loader import get_template

import pdfkit

from live_settings import signals
from live_settings.models import AbsenceCalendarSettings
from . import jobs
from .models import VacationLeaveDocument, VacationLeave, SpecialLeave, SpecialLeaveDocument
from intranet_project import general_functions


@receiver(signals.absence_calendar_schedule_changed, sender=AbsenceCalendarSettings)
def on_absence_calendar_settings_changed(sender, instance, **kwargs):
    jobs.reschedule_saving_leaves_documents()


@receiver(post_save, sender=VacationLeaveDocument)
def on_vacation_leave_document_created_create_pdf_in_archive(sender, instance, **kwargs):
    has_vacation_leave = general_functions.get_related_object_or_none(instance, VacationLeave, 'vacation_leave')

    if has_vacation_leave:
        year = str(instance.date_of_completion.year)
        month = str(instance.date_of_completion.month)
        day = str(instance.date_of_completion.day)

        path = os.path.join(
            settings.ABSENCE_CALENDAR_VACATION_LEAVE_APPLICATIONS_DIR,
            year, month,
        )

        Path(path).mkdir(parents=True, exist_ok=True)
        filename = f'{year}_{month}_{day}_{instance.absent_name.replace(" ", "_")}_' \
                    f'{instance.document_id}_{uuid.uuid4().hex}.pdf'

        options = {
            'page-size': 'A4',
            'dpi': 400,
            'encoding': 'UTF-8',
            'quiet': '',
        }

        context = {
            'vacation_leave': instance.vacation_leave,
            'download_mode': True,
            'city': instance.city,
        }

        template_path = 'absence_calendar/vacation_leave_application_detail.html'
        template = get_template(template_path)
        
        pdfkit.from_string(template.render(context), os.path.join(path, filename), options=options)


@receiver(post_save, sender=SpecialLeaveDocument)
def on_special_leave_document_created_create_pdf_in_archive(sender, instance, **kwargs):
    has_special_leave = general_functions.get_related_object_or_none(instance, SpecialLeave, 'special_leave')

    if has_special_leave:
        year = str(instance.date_of_completion.year)
        month = str(instance.date_of_completion.month)
        day = str(instance.date_of_completion.day)

        path = os.path.join(
            settings.ABSENCE_CALENDAR_SPECIAL_LEAVE_APPLICATIONS_DIR,
            year, month,
        )

        Path(path).mkdir(parents=True, exist_ok=True)
        filename = f'{year}_{month}_{day}_{instance.absent_name.replace(" ", "_")}_' \
                    f'{instance.document_id}_{uuid.uuid4().hex}.pdf'

        options = {
            'page-size': 'A4',
            'dpi': 400,
            'encoding': 'UTF-8',
            'quiet': '',
        }

        context = {
            'special_leave': instance.special_leave,
            'download_mode': True,
            'city': instance.city,
        }

        template_path = 'absence_calendar/special_leave_application_detail.html'
        template = get_template(template_path)
        
        pdfkit.from_string(template.render(context), os.path.join(path, filename), options=options)
