import os
from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from employee.models import User
from consultant.models import Consultant
from utils_app.models import TimeStampedModel
from activity.models import Comment, ConsultantComment


PETITION_TYPES = (
    ('gc', 'Green Card'),
    ('h1b_fresh', 'H1B New'),
    ('h1b_transfer', 'H1B Transfer'),
    ('h1b_extension', 'H1B Extension'),
    ('h1b_amendment', 'H1B Amendment'),
    ('h1b_cap_exempt', 'H1B Cap Exempt'),
)

PETITION_STATUSES = (
    ('new', 'New'),
    ('rfe', 'RFE'),
    ('denied', 'Denied'),
    ('shipped', 'Shipped'),
    ('approved', 'Approved'),
    ('assigned', 'Assigned'),
    ('reviewed', 'Reviewed'),
    ('lca_filed', 'LCA Filed'),
    ('print', 'Sent for Print'),
    ('lca_approved', 'LCA Approved'),
    ('under_review', 'Under Review'),
    ('rfe_responded', 'RFE Docs Sent'),
    ('doc_acknowledged', 'Docs Acknowledged'),
    ('doc_request_sent', 'Document Request Sent'),
    ('rfe_doc_acknowledged', 'RFE Docs Acknowledged'),
)


def attachment_upload(instance, filename):
    """Stores the attachment in a "per module/appname/primary key" folder"""
    if instance.petition:
        return f'attachments/visa_petition/{instance.petition.pk}/{filename}'
    return None


class Types(models.Model):
    name = models.CharField(_('Name '), max_length=40, null=True, blank=True)
    category = models.CharField(_('Category '), max_length=100, null=True, blank=True)
    display_name = models.CharField(_('Display Name'), max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.category}"

    class Meta:
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'


class Petition(TimeStampedModel):
    comments = GenericRelation(Comment, verbose_name="comments")
    is_active = models.BooleanField(_('Is Petition Active'), default=True)
    lca_no = models.CharField(_('LCA No.'), max_length=40, null=True, blank=True)
    employer = models.CharField(_('Employer'), max_length=20, default='Consultadd')
    status = models.CharField(_('Status'), choices=PETITION_STATUSES, max_length=20)
    uscis_no = models.CharField(_('USCIS No.'), max_length=40, null=True, blank=True)
    fedex_no = models.CharField(_('Fedex No.'), max_length=40, null=True, blank=True)
    premium_processing = models.BooleanField(_('Premium Processing'), default=None, null=True)
    consultant_comments = GenericRelation(ConsultantComment, verbose_name="consultant_comments")
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
        return f'{self.beneficiary.name} :: {self.status}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Petition, self).save(*args, **kwargs)


class Reason(TimeStampedModel):
    petition_status = models.CharField(_('Petition Status'), choices=PETITION_STATUSES, max_length=20)
    reason = models.TextField(_('Reason for Status'), null=True, blank=True)
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE,
        related_name='reasons',
        verbose_name='Petition',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Created By',
        related_name='reason',
        default=None, null=True,
    )

    def __str__(self):
        return f'{self.petition.id} :: {self.petition.status} :: {self.reason}'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Reason, self).save(*args, **kwargs)


class DocumentList(models.Model):
    created = models.DateTimeField(_('Created'), default=timezone.now)
    to_show = models.BooleanField(_('Show to Consultant'), default=True)
    doc_type = models.ForeignKey(
        Types, on_delete=models.CASCADE,
        verbose_name='Document Type',
        related_name='doc_list'
    )
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE,
        related_name='document_list',
        verbose_name='Petition',
    )

    def __str__(self):
        return f"{self.doc_type.name} - {self.petition.beneficiary.name}"


class Document(TimeStampedModel):
    remark = models.TextField(_('Remark'), null=True, blank=True)
    verified = models.BooleanField(_('Is File Verified'), default=None, null=True)
    file = models.FileField(_('attachment'), upload_to=attachment_upload, blank=True, null=True, default=None)
    doc_type = models.ForeignKey(
        Types, on_delete=models.CASCADE,
        verbose_name='Document Type',
        related_name='document'
    )
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='petition_documents',
        verbose_name='Uploaded By',
        default=None, null=True,
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
