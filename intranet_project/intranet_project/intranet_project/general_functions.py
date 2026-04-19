import os
import uuid
import logging

from datetime import datetime
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import get_template 
from django.http import HttpResponse
from django.conf import settings
import pdfkit
import random
import pathlib

from scheduler.models import JobLog


def validated_date(date_str):
    try:
        return datetime.strptime(date_str, settings.DATE_BACKEND_FORMAT).date()
    except ValueError:
        raise Http404(_('This page does not exist.'))


def validated_date_else_none(date_str):
    try:
        return datetime.strptime(date_str, settings.DATE_BACKEND_FORMAT).date()
    except ValueError:
        return None


def validated_datetime_else_none(date_str):
    try:
        return datetime.strptime(date_str, settings.DATETIME_BACKEND_FORMAT)
    except ValueError:
        return None


def earlier_date(date1, date2):
    return date1 if date1 < date2 else date2


def later_date(date1, date2):
    return date1 if date1 > date2 else date2


def current_date():
    return timezone.localtime(timezone.now()).date()


def current_time():
    return timezone.localtime(timezone.now()).time()


def current_datetime():
    return timezone.localtime(timezone.now())


def fill_date_kwarg(kwargs, kwarg_name, date_str):
    validated_date = validated_date_else_none(date_str)

    if validated_date:
        kwargs[kwarg_name] = validated_date


def fill_datetime_kwarg(kwargs, kwarg_name, datetime_str):
    validated_datetime = validated_datetime_else_none(datetime_str)

    if validated_datetime:
        kwargs[kwarg_name] = validated_datetime


def get_pdf_response(options, context, template_path, filename):
    template = get_template(template_path)

    pdf = pdfkit.PDFKit(template.render(context), 'string', options=options).to_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename={filename}.pdf'
    
    return response


def get_error_message(exception, default_message):
    error = str(exception)
    print(error)

    try:
        quote_left = error.index('"') + 1
        quote_right = error.rindex('"')
        return error[quote_left:quote_right]
    except (IndexError, ValueError) as e:
        return default_message


def get_object_or_none(model_type, *args, **kwargs):
    try:
        return model_type.objects.get(*args, **kwargs)
    except model_type.DoesNotExist:
        return None
    except model_type.MultipleObjectsReturned:
        return model_type.objects.filter(*args, **kwargs).first()


def get_related_object_or_none(model_object, related_model_type, attribute):
    try:
        return getattr(model_object, attribute)
    except (related_model_type.DoesNotExist, AttributeError):
        return None


def binary_search(iterable, to_find, key=None):
    if key:
        if hasattr(iterable, 'sort'):
            iterable.sort(key=key)
            
        return bin_search_key(iterable, 0, len(iterable)-1, to_find, key)
    else:
        iterable.sort()
        return bin_search(iterable, 0, len(iterable)-1, to_find)


def bin_search_key(iterable, low, high, to_find, key):
    if high >= low:
        mid = (high + low) // 2

        if key(iterable[mid]) == to_find:
            return iterable[mid]
        elif key(iterable[mid]) > to_find:
            return bin_search_key(iterable, low, mid-1, to_find, key)
        else:
            return bin_search_key(iterable, mid+1, high, to_find, key)
    else:
        return None


def bin_search(iterable, low, high, to_find):
    if high >= low:
        mid = (high + low) // 2

        if iterable[mid] == to_find:
            return iterable[mid]
        elif iterable[mid] > to_find:
            return bin_search(iterable, low, mid-1, to_find)
        else:
            return bin_search(iterable, mid+1, high, to_find)
    else:
        return None


def get_random_password(size):
    choices = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%^*(-_=+)'
    return ''.join([random.choice(choices) for i in range(size)])


def get_list_of_objects_without_duplicates(objects, lambda_fnc):
    values_without_duplicates = []
    objects_without_duplicates = []

    for obj in objects:
        value = lambda_fnc(obj)

        if value not in values_without_duplicates:
            values_without_duplicates.append(value)
            objects_without_duplicates.append(obj)

    return objects_without_duplicates


def get_uppercase_random_string(length):
    uppercase_choices = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    return ''.join([random.choice(uppercase_choices) for i in range(length)])


def get_file_extension(filename):
    extension = ''.join([s for s in pathlib.Path(filename).suffixes if not ' ' in s])

    return extension if not None else ''


def get_human_readable_file_size(value):
    if value < 512000:
        value = value / 1024.0
        extension = 'KB'
    elif value < 4194304000:
        value = value / 1048576.0
        extension = 'MB'
    else:
        value = value / 1073741824.0
        extension = 'GB'

    return f'{str(round(value, 2))} {extension}'


def log_job_info(logger, job_id, message):
    logger.info(message)
    JobLog.info(job_id, message)


def log_job_exception(logger, job_id, message):
    logger.exception(message)
    JobLog.exception(job_id, message)

def log_job_warning(logger, job_id, message):
    logger.warning(message)
    JobLog.warning(job_id, message)

def log_job_error(logger, job_id, message):
    logger.error(message)
    JobLog.error(job_id, message)
