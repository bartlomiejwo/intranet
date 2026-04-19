import os
import hashlib
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.db.models import F

from intranet_project import general_functions
from live_settings.global_live_settings import global_live_settings
from files_management import validation_codes
from users import models as users_models


def get_file_path(instance, filename):
    filename_on_server = IntranetFile.get_filename_on_server(instance, filename)
    first_subdir_name = general_functions.get_uppercase_random_string(2)
    second_subdir_name = general_functions.get_uppercase_random_string(2)

    return os.path.join(
        settings.FILES_MANAGEMENT_DIR_NAME,
        first_subdir_name, second_subdir_name,
        filename_on_server
    )


class IntranetFile(models.Model):
    class Meta:
        verbose_name = _('intranet file')
        verbose_name_plural = _('intranet files')

    name = models.CharField(max_length=250, verbose_name=_('name'))
    file = models.FileField(upload_to=get_file_path, verbose_name=_('file'))
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name=_('owner'))
    upload_date = models.DateTimeField(default=timezone.now, verbose_name=_('upload date'))
    added_with_wysiwyg = models.BooleanField(default=False, verbose_name=_('added with wysiwyg'))
    usage_counter = models.IntegerField(default=0, verbose_name=_('usage counter'))
    file_size = models.PositiveBigIntegerField(default=0, verbose_name=_('file size'))
    extension = models.CharField(max_length=20, blank=True, default='', verbose_name=_('extension'))
    file_content_hash = models.CharField(max_length=128, null=True, blank=True, default=None,
                                        verbose_name=_('file content hash'))

    def clean(self):
        if self.file:
            self.validate_size()
            if self.owner:
                self.validate_if_user_file_was_already_uploaded()
                self.validate_owner_files_capacity_limit()

    def validate_size(self):
        maximum_size_in_bytes = global_live_settings.files_management.max_file_size * 1024 * 1024

        if self.file.size > maximum_size_in_bytes:
            raise ValidationError(
                    _('File is too big. Maximum file size: %(max_file_size)s MB.'),
                    code=validation_codes.MAXIMUM_FILE_SIZE_EXCEEDED,
                    params={'max_file_size': str(global_live_settings.files_management.max_file_size)}
                )

    def validate_if_user_file_was_already_uploaded(self):
        self.file_content_hash = IntranetFile.get_file_hash_sha1(self.file)

        user_file_with_same_hash = general_functions.get_object_or_none(
            IntranetFile,
            owner=self.owner,
            file_content_hash=self.file_content_hash,
        )

        if user_file_with_same_hash:
            link = user_file_with_same_hash.get_link()
            validation_error = ValidationError(
                mark_safe(
                    _('You have already posted this file before, you can access it below this link: ') \
                        + f'<a href="{link}">{link}</a>'
                ),
                code=validation_codes.FILE_ALREADY_POSTED_BEFORE,
            )
            validation_error.link = link

            raise validation_error

    def validate_owner_files_capacity_limit(self):
        owner_profile = general_functions.get_related_object_or_none(
                                            self.owner, users_models.Profile, 'profile')

        if owner_profile:
            files_capacity_limit_in_bytes = owner_profile.files_capacity_limit * 1024 * 1024
            files_capacity_usage = IntranetFile.get_user_files_capacity_usage(self.owner)

            if files_capacity_usage + self.file.size > files_capacity_limit_in_bytes:
                raise ValidationError(
                        _('You have exceeded files capacity limit.'),
                        code=validation_codes.FILES_CAPACITY_LIMIT_EXCEEDED,
                    )

    def get_link(self):
        return self.file.url

    def get_type(self):
        extension = self.extension

        if len(extension) > 0 and extension[0] == '.':
            extension = extension[1:]

        return extension if extension else _('Unknown')

    def get_size_str(self):
        value = self.file_size

        return general_functions.get_human_readable_file_size(value)

    def increment_usage(self):
        self.usage_counter = F('usage_counter') + 1

    def decrement_usage(self):
        self.usage_counter = F('usage_counter') - 1

    def __str__(self):
        return self.name

    @staticmethod
    def increment_files_usage(intranet_files):
        for intranet_file in intranet_files:
            intranet_file.increment_usage()

        IntranetFile.objects.bulk_update(intranet_files, ['usage_counter',])

    @staticmethod
    def decrement_files_usage(intranet_files):
        for intranet_file in intranet_files:
            intranet_file.decrement_usage()

        IntranetFile.objects.bulk_update(intranet_files, ['usage_counter',])
    
    @staticmethod
    def get_user_files_capacity_usage(user):
        files = IntranetFile.objects.filter(owner=user)
        size_sum = 0

        for f in files:
            size_sum += f.file.size
        
        return size_sum

    @staticmethod
    def get_filename_on_server(instance, filename):
        filename_on_server = ''

        if hasattr(instance, 'name'):
            filename_on_server += os.path.splitext(os.path.basename(instance.name))[0] + '_'

        filename_on_server += uuid.uuid4().hex

        if hasattr(instance, 'owner'):
            if instance.owner:
                filename_on_server += '_' + str(instance.owner.id)

        extension = general_functions.get_file_extension(filename)
        filename_on_server += extension
        
        return filename_on_server

    @staticmethod
    def get_file_hash_sha1(file_to_hash):
        file_hash = hashlib.sha1()

        if file_to_hash.multiple_chunks():
            for chunk in file_to_hash.chunks():
                file_hash.update(chunk)
        else:    
            file_hash.update(file_to_hash.read())

        return file_hash.hexdigest()
