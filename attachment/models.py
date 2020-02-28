import os
import logging
from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from employee.models import User
from utils_app.models import TimeStampedModel

logger = logging.getLogger(__name__)

ATTACHMENT_TYPE = (
    ('ssn', 'SSN'),
    ('resume', 'Resume'),
    ('visa', 'Visa Docs'),
    ('msa', 'MSA/Agreement'),
    ('misc', 'Miscellaneous'),
    ('timesheet', 'Timesheet'),
    ('work_order', 'Work Order'),
    ('academic', 'Academic Docs'),
    ('photo_id', 'Miscellaneous'),
    ('results', 'Assessment Results'),
    ('msa_signed', 'MSA/Agreement Signed'),
    ('recordings', 'Interview Recordings'),
    ('work_order_signed', 'Work Order Signed'),
    ('work_order_msa', 'Work Order and MSA/Agreement'),
    ('work_order_msa_signed', 'Work Order and MSA/Agreement Signed'),
)


def attachment_upload(instance, filename):
    """Stores the attachment in a "per module/appname/primary key" folder"""
    return 'attachments/{app}_{model}/{pk}/{filename}'.format(
        app=instance.content_object._meta.app_label,
        model=instance.content_object._meta.object_name.lower(),
        pk=instance.content_object.pk,
        filename=filename,
    )


def create_attachment(data):
    try:
        content_type = ContentType.objects.get(model=data['model'])
        Attachment.objects.create(
            creator=data['creator'],
            content_type=content_type,
            object_id=data['object_id'],
            attachment_file=data['file'],
            attachment_type=data['type'],
        )
        return True
    except Exception as error:
        logger.error(error)
        return False


class AttachmentManager(models.Manager):
    def attachments_for_object(self, obj):
        object_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type__pk=object_type.id, object_id=obj.pk)


class Attachment(TimeStampedModel):
    objects = AttachmentManager()

    object_id = models.PositiveIntegerField()
    attachment_file = models.FileField(_('attachment'), upload_to=attachment_upload)
    attachment_type = models.CharField(choices=ATTACHMENT_TYPE, blank=True, null=True, max_length=500)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name='Model Name'
    )
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="created_attachments"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")
        ordering = ['-created']
        permissions = (
            ('delete_foreign_attachments', _('Can delete foreign attachments')),
        )

    def __str__(self):
        return f'{self.creator.employee_name} attached {self.attachment_file.name}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Attachment, self).save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.split(self.attachment_file.name)[1]


@receiver(models.signals.post_delete, sender=Attachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    """
    if instance.attachment_file:
        if os.path.isfile(instance.attachment_file.path):
            os.remove(instance.attachment_file.path)
