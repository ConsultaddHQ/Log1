from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from employee.models import User
from marketing.models import Submission
from consultant.models import Consultant
from attachment.models import Attachment, attachment_upload
from utils_app.models import TimeStampedModel

PROJECT_STATUS_CHOICES = (
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

TIMESHEET_STATUS = (
    ('draft', 'Draft'),
    ('rejected', 'Rejected'),
    ('submitted', 'Submitted'),
    ('pending_approval', 'Pending Approval'),
    ('consultant_rejected', 'Consultant Rejected'),
    ('consider_for_payroll', 'Consider for Payroll'),
    ('consider_for_invoice', 'Consider for Invoice'),
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
    is_msg_sent = models.BooleanField(
        _('Is Message Sent'),
        help_text='Message sent on Offer-announcement channel ?',
        default=False)
    submission = models.OneToOneField(
        Submission, on_delete=models.PROTECT,
        related_name='project',
        verbose_name='Submission'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='projects',
        verbose_name='Consultant',
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        self.modified = timezone.now()
        return super(Project, self).save(*args, **kwargs)

    def __str__(self):
        if self.consultant:
            return f'{self.id}: {self.consultant.name}'
        return f'{self.id}'

    @property
    def marketer_name(self):
        return self.submission.created_by.employee_name


class ProjectStatus(models.Model):
    is_current = models.BooleanField(_('Is Current'), default=True)
    created = models.DateTimeField(_('Created'), default=timezone.now)
    status = models.CharField(
        _('Status'),
        default='new', max_length=50,
        choices=PROJECT_STATUS_CHOICES,
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='statuses',
        verbose_name='Project'
    )

    class Meta:
        ordering = ('project',)
        verbose_name_plural = 'Project Statuses'


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
        return f'{self.id}:{self.project.submission.consultant.name} - {self.support.employee_name}'


class TimeSheet(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    end = models.DateField(_('End'), null=True, blank=True)
    start = models.DateField(_('Start'), null=True, blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    remark = models.TextField(_("Remark"), null=True, blank=True)
    hours = models.FloatField(max_length=20, null=True, blank=True)
    additional_hours = models.FloatField(max_length=20, null=True, blank=True, default=0)
    status = models.CharField(_("Status"), max_length=30, choices=TIMESHEET_STATUS, default='draft')
    status_updated_at = models.DateTimeField(_('Edited At'), null=True, blank=True)
    status_updated_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='timesheet_edits',
        verbose_name='Edited BY',
        null=True, blank=True
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='timesheets',
        verbose_name='Project'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(TimeSheet, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.project.consultant.name} - {self.hours}'


class PayrollSchedule(models.Model):
    pay_date = models.DateField(_('Pay Date'))
    pay_day = models.CharField(_('Pay day'), max_length=20)
    processing_date = models.DateField(_('Processing Date'))
    pay_period_end = models.DateField(_('Pay Period End Date'))
    pay_period_start = models.DateField(_('Pay Period Start Date'))

    def __str__(self):
        return f'{self.processing_date} :: {self.pay_period_start} - {self.pay_period_end} :: {self.pay_date}'
