import os
from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from employee.models import User
from consultant.models import Consultant
from utils_app.models import TimeStampedModel

DOCUMENT_TYPE = (
    ('other', 'Other'),
    ('resume', 'Resume'),
    ('visa', 'Visa Docs'),
    ('msa', 'MSA/Agreement'),
    ('photo_id', 'Photo Id'),
    ('misc', 'Miscellaneous'),
    ('timesheet', 'Timesheet'),
    ('work_order', 'Work Order'),
    ('academic', 'Academic Docs'),
)

PETITION_TYPES = (
    ('h1b_fresh', 'H1B New'),
    ('h1b_extension', 'H1B Extension'),
    ('h1b_amendment', 'H1B Amendment'),
)

PETITION_STATUSES = (
    ('new', 'New'),
    ('assigned', 'Assigned'),
    ('doc_request_sent', 'Document Request Sent'),
    ('lca_filed', 'LCA Filed'),
    ('lca_approved', 'LCA Approved'),
    ('under_review', 'Under Review'),
    ('reviewed', 'Reviewed'),
    ('print', 'Sent for Print'),
    ('shipped', 'Shipped'),
    ('doc_acknowledged', 'Docs Acknowledged'),
    ('rfe', 'RFE'),
    ('rfe_responded', 'RFE Docs Sent'),
    ('rfe_doc_acknowledged', 'RFE Docs Acknowledged'),
    ('approved', 'Approved'),
    ('denied', 'Denied'),
)


def attachment_upload(instance, filename):
    """Stores the attachment in a "per module/appname/primary key" folder"""
    if instance.petition:
        return f'attachments/visa_petition/{instance.petition.pk}/{filename}'
    return None


class Petition(TimeStampedModel):
    is_active = models.BooleanField(_('Is Petition Active'), default=True)
    lca_no = models.CharField(_('LCA No.'), max_length=40, null=True, blank=True)
    employer = models.CharField(_('Employer'), max_length=20, default='Consultadd')
    status = models.CharField(_('Status'), choices=PETITION_STATUSES, max_length=20)
    uscis_no = models.CharField(_('USCIS No.'), max_length=40, null=True, blank=True)
    fedex_no = models.CharField(_('Fedex No.'), max_length=40, null=True, blank=True)
    premium_processing = models.BooleanField(_('Premium Processing'), default=None, null=True)
    petition_type = models.CharField(_('Petition Type'), choices=PETITION_TYPES, max_length=20, blank=True, null=True)
    beneficiary_type = models.BooleanField(
        _('Beneficiary Type'), default=True,
        help_text=_('True for Consultant and False for In-house Employee')
    )
    beneficiary = models.ForeignKey(
        Consultant, on_delete=models.PROTECT,
        verbose_name='Beneficiary',
        related_name='petitions',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Created By',
        related_name='petitions',
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Assigned To',
        related_name='assigned_petitions',
    )

    def __str__(self):
        return f'{self.beneficiary.name} attached {self.status}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Petition, self).save(*args, **kwargs)


class Document(TimeStampedModel):
    file = models.FileField(_('attachment'), upload_to=attachment_upload, blank=True, null=True, default=None)
    doc_type = models.CharField(_('Document Type'), choices=DOCUMENT_TYPE, max_length=50)
    verified = models.BooleanField(_('Is File Verified'), default=False)
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='petition_documents',
        verbose_name='Uploaded By',
        blank=True, null=True,
    )
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Petition',
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.petition.beneficiary.name} attached {self.doc_type}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Document, self).save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.split(self.file.name)[1]


@receiver(models.signals.post_delete, sender=Document)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    """
    if instance.file:
        instance.file.storage.delete(instance.file.name)
