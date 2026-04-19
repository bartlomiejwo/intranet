from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

from .models import Page
from files_management.models import IntranetFile
from files_management.html_content_intranet_files_finder import HTMLContentIntranetFilesFinder
from intranet_project import general_functions


@receiver(pre_save, sender=Page)
def update_page_file_usage_counters(sender, instance, **kwargs):
    if instance.id is None:
        update_file_usage_counters_after_page_creation(instance)
    else:
        update_file_usage_counters_after_page_update(instance)

    
def update_file_usage_counters_after_page_creation(instance):
    added_files = get_intranet_files_included_in_page(instance)
    IntranetFile.increment_files_usage(added_files)


def update_file_usage_counters_after_page_update(instance):
    page_before_update = general_functions.get_object_or_none(Page, id=instance.id)

    files_before_update = get_intranet_files_included_in_page(page_before_update)
    files_after_update = get_intranet_files_included_in_page(instance)

    removed_files = files_before_update.difference(files_after_update)
    added_files = files_after_update.difference(files_before_update)

    IntranetFile.decrement_files_usage(removed_files)
    IntranetFile.increment_files_usage(added_files)


@receiver(post_delete, sender=Page)
def update_page_file_usage_counters_after_delete(sender, instance, **kwargs):
    removed_files = get_intranet_files_included_in_page(instance)
    IntranetFile.decrement_files_usage(removed_files)


def get_intranet_files_included_in_page(page):
    files_finder = HTMLContentIntranetFilesFinder()
    files_finder.feed(page.content)

    return files_finder.intranet_files
