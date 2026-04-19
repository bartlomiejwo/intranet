from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Post, Comment
from files_management.models import IntranetFile
from intranet_project import general_functions
from files_management.html_content_intranet_files_finder import HTMLContentIntranetFilesFinder


@receiver(pre_save, sender=Post)
def update_post_publication_date(sender, instance, **kwargs):
    if not instance.publication_date:
        instance.publication_date = instance.date_created


@receiver(pre_save, sender=Post)
def update_post_edit_date(sender, instance, **kwargs):
    if instance.id is not None:
        post_before_edit = general_functions.get_object_or_none(Post, id=instance.id)

        if post_before_edit:
            if instance.content != post_before_edit.content:
                instance.edit_date = timezone.now()


@receiver(pre_save, sender=Post)
def update_post_file_usage_counters(sender, instance, **kwargs):
    if instance.id is None:
        update_file_usage_counters_after_post_creation(instance)
    else:
        update_file_usage_counters_after_post_update(instance)

    
def update_file_usage_counters_after_post_creation(instance):
    added_files = get_intranet_files_included_in_post(instance)
    IntranetFile.increment_files_usage(added_files)


def update_file_usage_counters_after_post_update(instance):
    post_before_update = general_functions.get_object_or_none(Post, id=instance.id)

    files_before_update = get_intranet_files_included_in_post(post_before_update)
    files_after_update =get_intranet_files_included_in_post(instance)

    removed_files = files_before_update.difference(files_after_update)
    added_files = files_after_update.difference(files_before_update)

    IntranetFile.decrement_files_usage(removed_files)
    IntranetFile.increment_files_usage(added_files)


@receiver(post_delete, sender=Post)
def update_post_file_usage_counters_after_delete(sender, instance, **kwargs):
    removed_files = get_intranet_files_included_in_post(instance)
    IntranetFile.decrement_files_usage(removed_files)


def get_intranet_files_included_in_post(post):
    files_finder = HTMLContentIntranetFilesFinder()
    files_finder.feed(post.content)

    return files_finder.intranet_files


@receiver(pre_save, sender=Comment)
def update_comment_file_usage_counters(sender, instance, **kwargs):
    if instance.id is None:
        update_file_usage_counters_after_comment_creation(instance)
    else:
        update_file_usage_counters_after_comment_update(instance)


def update_file_usage_counters_after_comment_creation(instance):
    added_files = get_intranet_files_included_in_comment(instance)
    IntranetFile.increment_files_usage(added_files)


def update_file_usage_counters_after_comment_update(instance):
    comment_before_update = general_functions.get_object_or_none(Comment, id=instance.id)

    files_before_update = get_intranet_files_included_in_comment(comment_before_update)
    files_after_update = get_intranet_files_included_in_comment(instance)

    removed_files = files_before_update.difference(files_after_update)
    added_files = files_after_update.difference(files_before_update)

    IntranetFile.decrement_files_usage(removed_files)
    IntranetFile.increment_files_usage(added_files)


@receiver(post_delete, sender=Comment)
def update_comment_file_usage_counters_after_delete(sender, instance, **kwargs):
    removed_files = get_intranet_files_included_in_comment(instance)
    IntranetFile.decrement_files_usage(removed_files)


def get_intranet_files_included_in_comment(comment):
    files_finder = HTMLContentIntranetFilesFinder()
    files_finder.feed(comment.content)

    return files_finder.intranet_files


@receiver(pre_save, sender=Comment)
def update_comment_edit_date(sender, instance, **kwargs):
    if instance.id is not None:
        comment_before_edit = general_functions.get_object_or_none(Comment, id=instance.id)
        
        if comment_before_edit:
            if comment_before_edit.content != instance.content:
                instance.edit_date = timezone.now()
