from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from utils_app.models import TimeStampedModel

from employee.models import User


class Activity(models.Model):
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'

    ACTIVITY_TYPES = (
        (CREATED, 'Created'),
        (UPDATED, 'Updated'),
        (DELETED, 'Deleted'),
    )

    activity_type = models.CharField(_('Activity Type'), max_length=10, choices=ACTIVITY_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    desc = models.TextField(_('Activity Description'), )

    # Below the mandatory fields for generic relation
    object_id = models.PositiveIntegerField(_('Object Id'), )
    content_object = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)

    def __str__(self):
        return f'{self.content_type.model.title()} {self.get_activity_type_display()} by {self.user.employee_name}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        return super(Activity, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'activities'


class Comment(TimeStampedModel):
    comment_text = models.TextField(_('Comment Text'))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Comment done by'
    )
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='child_comments',
        help_text='Designates the id of comment on which child comment is made')

    # Below the mandatory fields for generic relation
    object_id = models.PositiveIntegerField(_('Object Id'), )
    content_object = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        """
            On save, update timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Comment, self).save(*args, **kwargs)

    def __str__(self):
        return self.user.employee_name
