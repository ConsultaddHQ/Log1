from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from marketing.models import Submission
from consultant.models import Consultant
from attachment.models import Attachment
from employee.models import User, Tagging
from utils_app.models import TimeStampedModel

FEEDBACK_CHOICES = (
    ('cfr', 'CFR'),
    ('issue', 'Issue'),
    ('2_week', '2 Week'),
    ('pre_joining', 'Pre Joining'),
    ('independent', 'Independent'),
    ('re_marketing', 'Re-marketing'),
    ('rate_increment', 'Rate Increment'),
)


class Project(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    rate = models.FloatField(_('Rate'), null=True, blank=True)
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    feedback = models.TextField(_('Reason of Failure'), null=True, blank=True)
    payment_term = models.IntegerField(_('Payment Term'), null=True, blank=True)
    client_address = models.TextField(_('Client Address'), null=True, blank=True)
    vendor_address = models.TextField(_('Vendor Address'), null=True, blank=True)
    is_remote = models.BooleanField(_('Is Remote Project'), null=True, blank=True)
    employer = models.CharField(_('Employer'), max_length=50, null=True, blank=True)
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
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Project, self).save(*args, **kwargs)

    def __str__(self):
        if self.consultant:
            return f'{self.id}: {self.consultant.name}'
        return f'{self.id}'

    @property
    def marketer_name(self):
        return self.submission.created_by.employee_name

    @property
    def created_by(self):
        return self.submission.created_by


class ProjectStatus(models.Model):
    PROJECT_STATUS_CHOICES = (
        ("new", "New"),
        ("other", "Other"),
        ("joined", "Joined"),
        ("signed", "Signed"),
        ("received", "Received"),
        ("extended", "Extended"),
        ("on_boarded", "On Boarded"),
        ("complete", "Project Completed"),

        # Offer cancelled
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
        ("terminated-fired", "Fired"),
        ("terminated-resigned", "Resigned"),
        ("terminated", "Project Terminated"),
        ("terminated-fired_budget_issue", "Fired - Budget Issue"),
        ("terminated-resigned_rate_issue", "Resigned - Rate Issue"),
        ("terminated-fired_security_issue", "Fired - Data Security Issue"),
        ("terminated-resigned_location_issue", "Resigned - Location Issue"),
        ("terminated-fired_performance_issue", "Fired - Performance Issue"),
        ("terminated-resigned_full_time_offer", "Resigned - Full Time Offer"),
        ("terminated-resigned_technology_issue", "Resigned - Technology Issue"),
    )
    is_current = models.BooleanField(_('Is Current'), default=True)
    created = models.DateTimeField(_('Created'), default=timezone.now)
    status = models.CharField(
        _('Status'),
        default='new', max_length=50,
        choices=PROJECT_STATUS_CHOICES,
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='statuses',
        verbose_name='Project'
    )

    class Meta:
        ordering = ('project',)
        verbose_name_plural = 'Project Statuses'


class ProjectOrder(TimeStampedModel):
    field = models.CharField(_('Field'), max_length=50, blank=True, null=True)
    value = models.CharField(_('Value'), max_length=100, blank=True, null=True)
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='order',
        verbose_name='Project'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='project_order',
        verbose_name='Project Order created by'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectOrder, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.value} - {self.field}'


class ProjectSupport(TimeStampedModel):
    feedback = models.TextField(_("Feedback"), null=True, blank=True)
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
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectSupport, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.project.submission.consultant.name} - {self.support.employee_name}'


class SupportStatus(models.Model):
    frequency = models.CharField(_('Frequency'), max_length=50)
    is_current = models.BooleanField(_('Is Current'), default=True)
    created = models.DateTimeField(_('Created'), default=timezone.now)
    change_date = models.DateField(_('Status Change Date'), blank=True, null=True)
    support = models.ForeignKey(
        ProjectSupport, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='statuses',
        verbose_name='Support'
    )

    def __str__(self):
        return f'{self.id}:{self.support.support.employee_name} - {self.frequency}'


class TimeSheet(TimeStampedModel):
    TIMESHEET_STATUS = (
        ('draft', 'Draft'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
        ('submitted', 'Submitted'),
    )
    attachments = GenericRelation(Attachment)
    start = models.DateField(_('Start'), null=True, blank=True)
    end = models.DateField(_('End'), null=True, blank=True)
    hours = models.FloatField(max_length=20, null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='timesheets',
        verbose_name='Project'
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    remark = models.TextField(_("Remark"), null=True, blank=True)
    submitted_at = models.DateTimeField(_('Submitted at'), null=True, blank=True)
    con_comment = models.TextField(_("Consultant Comment"), null=True, blank=True)
    status_updated_at = models.DateTimeField(_('Edited At'), null=True, blank=True)
    additional_hours = models.FloatField(max_length=20, null=True, blank=True, default=0)
    status = models.CharField(_("Status"), max_length=30, choices=TIMESHEET_STATUS, default='draft')
    status_updated_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='timesheet_edits',
        verbose_name='Edited BY',
        null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(TimeSheet, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.project.consultant.name} - {self.status}'


class PayrollSchedule(models.Model):
    pay_date = models.DateField(_('Pay Date'))
    pay_day = models.CharField(_('Pay day'), max_length=20)
    processing_date = models.DateField(_('Processing Date'))
    pay_period_end = models.DateField(_('Pay Period End Date'))
    pay_period_start = models.DateField(_('Pay Period Start Date'))

    def __str__(self):
        return f'{self.processing_date} :: {self.pay_period_start} - {self.pay_period_end} :: {self.pay_date}'


class ConsultantFeedback(TimeStampedModel):
    tagged_user = GenericRelation(Tagging)
    description = models.TextField(_('Feedback'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE)
    verdict = models.CharField(_('Consultant Verdict'), max_length=30, null=True, blank=True)
    department = models.CharField(_('Feedback Department'), max_length=30, null=True, blank=True)
    feedback_type = models.CharField(_('Feedback Type'), max_length=30, choices=FEEDBACK_CHOICES)
    rating = models.IntegerField(_('Consultant Rating'), help_text=_('Rating 1 being worst and 5 being best'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantFeedback, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name}:{self.feedback_type}'
