import os

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import IntranetFile
from intranet_project import general_functions
from live_settings import signals
from live_settings.models import FilesManagementSettings
from . import jobs


@receiver(pre_save, sender=IntranetFile)
def fill_file_meta_info(sender, instance, **kwargs):
    instance.file_size = instance.file.size
    
    name_ext = general_functions.get_file_extension(instance.name)
    if not name_ext:
        filename_ext = general_functions.get_file_extension(instance.file.path)

        if filename_ext:
            instance.extension = filename_ext
            instance.name += filename_ext
    else:
        instance.extension = name_ext

    if instance.file_content_hash is None:
        instance.file_content_hash = IntranetFile.get_file_hash_sha1(instance.file)


@receiver(pre_save, sender=IntranetFile)
def delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_file = IntranetFile.objects.get(pk=instance.pk).file
    except IntranetFile.DoesNotExist:
        return False
    else:
        new_file = instance.file

        if old_file:
            if not old_file.path == new_file.path:
                if os.path.isfile(old_file.path):
                    os.remove(old_file.path)


@receiver(post_delete, sender=IntranetFile)
def delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(signals.files_management_schedule_changed, sender=FilesManagementSettings)
def on_files_management_settings_changed(sender, instance, **kwargs):
    jobs.reschedule_removing_unused_files()
