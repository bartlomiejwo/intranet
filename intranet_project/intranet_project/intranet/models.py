from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext
from tinymce.models import HTMLField

from intranet import validation_codes
from intranet_project import general_functions


class Post(models.Model):
    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')
        permissions = (
            ('can_pin_post', 'Can pin post'),
        )

    content = HTMLField(verbose_name=_('content'))
    date_created = models.DateTimeField(default=timezone.now, verbose_name=_('date created'))
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('author'))
    comments_allowed = models.BooleanField(default=True, verbose_name=_('comments allowed'))
    likes_allowed = models.BooleanField(default=True, verbose_name=_('likes allowed'))
    published = models.BooleanField(default=True, verbose_name=_('published'))
    publication_date = models.DateTimeField(default=None, null=True, blank=True, verbose_name=_('publication date'))
    expiration_date = models.DateTimeField(default=None, null=True, blank=True, verbose_name=_('expiration date'))
    edit_date = models.DateTimeField(default=None, null=True, blank=True, verbose_name=_('edit date'))
    pinned = models.BooleanField(default=False, verbose_name=_('pinned'))

    def clean(self):
        self.validate_expiration_date_is_later_than_publication_date()

    def validate_expiration_date_is_later_than_publication_date(self):
        if self.publication_date and self.expiration_date:
            if self.publication_date > self.expiration_date:
                raise ValidationError(
                            _('Expiration date cannot be earlier than publication date.'),
                            code=validation_codes.EXPIRATION_DATE_EARLIER_THAN_PUBLICATION_DATE,
                        )

    def get_likes(self):
        return Like.objects.filter(post=self).count()

    def user_liked(self, user):
        like = general_functions.get_object_or_none(Like, post=self, user=user)

        return True if like is not None else False
    
    def is_published(self):
        if not self.published:
            return False

        now = timezone.now()
        pub_date = self.publication_date if self.publication_date is not None else now
        exp_date = self.expiration_date if self.expiration_date is not None \
            else now + timezone.timedelta(minutes=1)
        
        if pub_date <= now and exp_date > now:
            return True

        return False

    def __str__(self):
        return f'{self.author} - {self.content[:10]}...' 
    
    def get_absolute_url(self):
        return reverse('intranet:post_detail', kwargs={'pk': self.pk})


class Comment(models.Model):
    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ['-date_posted',]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name=_('post'))
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('author'))
    content = HTMLField(verbose_name=_('content'))
    date_posted = models.DateTimeField(default=timezone.now, verbose_name=_('date posted'))
    edit_date = models.DateTimeField(default=None, null=True, blank=True, verbose_name=_('edit date'))

    def clean(self):
        try:
            Comment.validate_post_allowed_to_comment(self.post)
        except Post.DoesNotExist:
            pass
        
    @staticmethod
    def validate_post_allowed_to_comment(post):
        if not post.comments_allowed:
            raise ValidationError(
                    _('The post you want to comment on has the comment option turned off.'),
                    code=validation_codes.POST_HAS_COMMENTS_TURNED_OFF,
                )

    def get_likes(self):
        return Like.objects.filter(comment=self).count()

    def user_liked(self, user):
        like = general_functions.get_object_or_none(Like, comment=self, user=user)

        return True if like is not None else False

    def __str__(self):
        return f'Comment created by {self.author.username} on {self.date_posted}'


class Like(models.Model):
    class Meta:
        verbose_name = _('like')
        verbose_name_plural = _('likes')
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_like_post'),
            models.UniqueConstraint(fields=['user', 'comment', ], name='unique_like_comment')
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('user'))

    post = models.ForeignKey(Post, default=None, null=True, blank=True, on_delete=models.CASCADE,
                            verbose_name=_('post'))
    comment = models.ForeignKey(Comment, default=None, null=True, blank=True, on_delete=models.CASCADE,
                                verbose_name=_('comment'))
    timestamp = models.DateTimeField(default=timezone.now, verbose_name=_('timestamp'))

    def clean(self):
        self.validate_exactly_one_object_liked()
        self.validate_post_liking_allowed()

    def validate_exactly_one_object_liked(self):
        number_of_liked_objects = self.get_number_of_liked_objects()

        if number_of_liked_objects != 1:
            raise ValidationError(
                    _('Exactly one object should be liked.'),
                    code=validation_codes.MORE_OR_LESS_THAN_ONE_OBJECT_LIKED,
                )

    def validate_post_liking_allowed(self):
        if self.post is not None:
            if not self.post.likes_allowed:
                raise ValidationError(
                        _('The post you want to like has likes turned off.'),
                        code=validation_codes.POST_HAS_LIKES_TURNED_OFF,
                    )

    def get_number_of_liked_objects(self):
        number_of_liked_objects = 0

        if self.post is not None:
            number_of_liked_objects += 1
        
        if self.comment is not None:
            number_of_liked_objects += 1

        return number_of_liked_objects

    def get_object(self):
        if self.post is not None:
            return self.post
        
        if self.comment is not None:
            return self.comment

        return None

    def __str__(self):
        return f'{self.get_object()} like by {self.user}'
