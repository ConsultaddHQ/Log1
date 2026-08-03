from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import ugettext_lazy as _

from consultant.models import Consultant


class CkillerSubmission(models.Model):
    sub_created = models.DateTimeField()
    submission_id = models.PositiveIntegerField(_('Submission ID'))
    interview = ArrayField(models.TextField(), null=True, blank=True)
    project = models.BooleanField(_('Project'), null=True, blank=True)
    rate = models.FloatField(_('Rate'), max_length=20, null=True, blank=True)
    employer = models.CharField(_('Employer'), max_length=20, null=True, blank=True)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)
    job_title = models.CharField(_('Job Title'), max_length=300, null=True, blank=True)
    marketer = models.CharField(_('Marketer Name'), max_length=50, null=True, blank=True)
    job_location = models.CharField(_('Job Title'), max_length=150, null=True, blank=True)
    marketing_email = models.CharField(_('Marketing Email'), max_length=50, null=True, blank=True)
    marketing_phone = models.CharField(_('Marketing Phone'), max_length=20, null=True, blank=True)
    consultant = models.ForeignKey(
        Consultant, null=True,
        blank=True, on_delete=models.CASCADE,
        related_name='log1_submissions',
        verbose_name='old_submissions'
    )

    def __str__(self):
        return "{} {}".format(self.consultant, self.job_title)


class CkillerVendorClient(models.Model):
    name = models.CharField(_('Vendor Company Name'), max_length=200)
    address = models.TextField(_('Vendor Address'), null=True, blank=True)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)
    type = models.CharField(_("Type"), max_length=10, choices=(('vendor', 'Vendor'), ('client', 'Client')))
    ckiller_sub = models.ForeignKey(
        CkillerSubmission, on_delete=models.CASCADE,
        related_name='vendors',
        verbose_name='submissions'
    )

    def __str__(self):
        return "{} {}".format(self.name, self.type)
