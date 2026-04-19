from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from .models import IntranetFile
from intranet_project import general_functions
from files_management import validation_codes
from users import models as users_models


class IntranetFileCreateForm(forms.ModelForm):

    class Meta:
        model = IntranetFile
        fields = ['name', 'file',]

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        super().__init__(*args, **kwargs)

    def clean(self):
        self.validate_if_user_file_was_already_uploaded()
        self.validate_owner_files_capacity_limit()

    def validate_if_user_file_was_already_uploaded(self):
        self.file_content_hash = IntranetFile.get_file_hash_sha1(self.cleaned_data.get('file'))

        user_file_with_same_hash = general_functions.get_object_or_none(
            IntranetFile,
            owner=self.owner,
            file_content_hash=self.file_content_hash,
        )

        if user_file_with_same_hash:
            link = user_file_with_same_hash.get_link()

            raise ValidationError(
                mark_safe(
                    _('You have already posted this file before, you can access it below this link: ') \
                        + f'<a href="{link}">{link}</a>'
                ),
                code=validation_codes.FILE_ALREADY_POSTED_BEFORE,
            )

    def validate_owner_files_capacity_limit(self):
        owner_profile = general_functions.get_related_object_or_none(
                                            self.owner, users_models.Profile, 'profile')

        if owner_profile:
            files_capacity_limit_in_bytes = owner_profile.files_capacity_limit * 1024 * 1024
            files_capacity_usage = IntranetFile.get_user_files_capacity_usage(self.owner)

            if files_capacity_usage + self.cleaned_data.get('file').size > files_capacity_limit_in_bytes:
                raise ValidationError(
                        _('You have exceeded files capacity limit.'),
                        code=validation_codes.FILES_CAPACITY_LIMIT_EXCEEDED,
                    )
