from datetime import datetime
from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE
from .models import Post, Comment


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = ['content', 'comments_allowed', 'likes_allowed',
                    'published', 'publication_date', 'expiration_date']
        widgets = {
            'publication_date': forms.DateInput(
                format=settings.DATETIME_BACKEND_FORMAT.replace(' ', 'T'),
                attrs={'type': 'datetime-local'}
            ),
            'expiration_date': forms.DateInput(
                format=settings.DATETIME_BACKEND_FORMAT.replace(' ', 'T'),
                attrs={'type': 'datetime-local'}
            ),
        }

    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), label=_('Content'))


class CommentCreateForm(forms.ModelForm):
    
    class Meta:
        model = Comment
        fields = ('content',)
        labels = {
            'content': '',
        }

    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post')

        super().__init__(*args, **kwargs)

    def clean(self):
        Comment.validate_post_allowed_to_comment(self.post)

    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30, 'class': 'tinymce-comment'}), label='')


class CommentUpdateForm(forms.ModelForm):
    
    class Meta:
        model = Comment
        fields = ('content',)
        labels = {
            'content': '',
        }

    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30, 'class': 'tinymce-comment'}), label='')

