from django.db import models
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext


def validate_position(to_validate, objects):
    if len(objects) > 0:
        raise ValidationError(
            _('Position %(value)s is already occupied by "%(object_name)s"'),
            params={'value': to_validate.position,
                    'object_name': objects.first().title},
        )


class Tab(models.Model):
    class Meta:
        verbose_name = _('tab')
        verbose_name_plural = _('tabs')

    title = models.CharField(max_length=40, unique=True, null=False, blank=False,
                            verbose_name=pgettext('title', 'the name of something'))
    area_name = models.CharField(max_length=40, unique=True, null=False, blank=False,
                validators=[validators.validate_slug], verbose_name=_('area name'))
    position = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=_('position'))

    def __str__(self):
        return self.title

    def clean(self):
        self.run_position_validation()

    def run_position_validation(self):
        tabs = Tab.objects.filter(position=self.position).exclude(pk=self.pk)
        validate_position(self, tabs)
        
        pages = Page.objects.filter(position=self.position, parent_tab=None)
        validate_position(self, pages)


class Page(models.Model):
    class Meta:
        verbose_name = _('page')
        verbose_name_plural = _('pages')

    parent_tab = models.ForeignKey(Tab, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('parent tab'))
    url = models.CharField(max_length=40, unique=True, null=False, blank=False, 
                            validators=[validators.validate_slug])
    title = models.CharField(max_length=40, null=False, blank=False,
                            verbose_name=pgettext('title', 'the name of something'))
    position = models.PositiveSmallIntegerField(null=False, blank=False, verbose_name=_('position'))
    content = models.TextField(null=False, blank=True, verbose_name=_('content'))

    def __str__(self):
        return self.title

    def clean(self):
        self.run_position_validation()

    def run_position_validation(self):
        if self.parent_tab is None:
            tabs = Tab.objects.filter(position=self.position)
            pages = Page.objects.filter(position=self.position, parent_tab=None).exclude(pk=self.pk)
            validate_position(self, tabs)
        else:
            pages = Page.objects.filter(position=self.position, parent_tab=self.parent_tab).exclude(pk=self.pk)
        
        validate_position(self, pages)
