from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from employee.models import User
from marketing.models import Submission
from consultant.models import Consultant
from attachment.models import Attachment
from utils_app.models import TimeStampedModel

PROJECT_CHOICES = (
    ("new", "New"),
    ("other", "Other"),
    ("joined", "Joined"),
    ("signed", "Signed"),
    ("received", "Received"),
    ("extended", "Extended"),
    ("on_boarded", "On Boarded"),
    ("complete", "Project Completed"),

    # offer cancelled
    ("cancelled", "Cancelled"),
    ("cancelled-dual_offer", "Dual Offer"),
    ("cancelled-client_cancelled", "Client Cancelled"),
    ("cancelled-contract_conflicts", "Contract Conflicts"),
    ("cancelled-candidate_absconded", "Candidate Absconded"),
    ("cancelled-candidate_denied", "Candidate Denied Joining"),
    ("cancelled_candidate_denied_jd", "Candidate Denied Joining - JD"),
    ("cancelled-candidate_denied_rate", "Candidate Denied Joining - Rate"),
    ("cancelled-candidate_denied_location", "Candidate Denied Joining - Location"),

    # PO terminated
    ("terminated-resigned", "Resigned"),
    ("terminated", "Project Terminated"),
    ("terminated-resigned_rate_issue", "Resigned - Rate Issue"),
    ("terminated-resigned_location_issue", "Resigned - Location Issue"),
    ("terminated-resigned_full_time_offer", "Resigned - Full Time Offer"),
    ("terminated-resigned_technology_issue", "Resigned - Technology Issue"),
    ("terminated-fired_budget_issue", "Fired - Budget Issue"),
    ("terminated-fired_performance_issue", "Fired - Performance Issue"),
    ("terminated-fired_security_issue", "Fired - Data Security Issue"),
)


class Project(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    feedback = models.TextField(_('Reason of Failure'), null=True, blank=True)
    payment_term = models.IntegerField(_('Payment Term'), null=True, blank=True)
    client_address = models.TextField(_('Client Address'), null=True, blank=True)
    vendor_address = models.TextField(_('Vendor Address'), null=True, blank=True)
    city = models.CharField(_('Client City'), max_length=100, blank=True, null=True)
    duration = models.CharField(_('Duration'), max_length=50, null=True, blank=True)
    reporting_details = models.TextField(_('Reporting Details'), null=True, blank=True)
    invoicing_period = models.IntegerField(_('Invoicing Period'), null=True, blank=True)
    status = models.CharField(
        _('Status'), max_length=50,
        choices=PROJECT_CHOICES,
        default='new', null=True, blank=True
    )
    submission = models.OneToOneField(
        Submission, on_delete=models.PROTECT,
        related_name='project',
        verbose_name='Submission'
    )
    consultant = models.OneToOneField(
        Consultant, on_delete=models.PROTECT,
        related_name='projects',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        self.modified = timezone.now()
        return super(Project, self).save(*args, **kwargs)

    def __str__(self):
        return self.consultant.name

    @property
    def marketer_name(self):
        return self.submission.lead.marketer.employee_name

    @property
    def consultant_name(self):
        return self.submission.lead.marketer.employee_name


class ProjectSupport(TimeStampedModel):
    end = models.DateField(_('Support End Date'), blank=True, null=True)
    start = models.DateField(_('Support Start Date'), blank=True, null=True)
    support = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='projects',
        verbose_name='Support Point of Contact'
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='support',
        verbose_name='Project'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectSupport, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.project.submission.consultant.name} - {self.support.employee_name}'

