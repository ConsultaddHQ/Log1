from datetime import date
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from consultant.models import Consultant
from attachment.models import Attachment
from employee.models import User, Tagging
from marketing.models import Submission, Interview
from utils_app.models import TimeStampedModel, Choice

FEEDBACK_CHOICES = (
    ('cfr', 'CFR'),
    ('monthly', 'Monthly'),
    ('green_card', 'Green Card'),
    ('independent', 'Independent'),
    ('pre_joining', 'Pre Joining'),
    ('2_week', '2 Week of Joining'),
    ('re_marketing', 'Re-marketing'),
    ('rate_increment', 'Rate Increment'),
    ('engineering_issue', 'Engineering Issue'),
)

STAKEHOLDER = {
    "VP": {"query": "vp", "role": "vp"},
    "Lead SM": {"query": "lead_sm", "role": "lead_sm"},
    "Team Lead": {"query": "team_lead", "role": "admin"},
    "Marketer": {"query": "marketer", "role": "marketer"},
    "Recruiter": {"query": "recruiter", "role": "recruiter"},
    "Coder": {"query": "interviews__guests__user", "role": "engineer"},
    "Supervisor": {"query": "interviews__supervisor", "role": "interviewee"},
    "Support Person": {"query": "support_persons__support", "role": "engineer"},
}


DURATION_COMPLETION_NOTIFICATION_TYPE = [
    {"hour": 160, "du_check": "160_HOUR"}, {"hour": 320, "du_check": "320_HOUR"},
    {"hour": 480, "du_check": "480_HOUR"}, {"hour": 640, "du_check": "640_HOUR"}, {"hour": 800, "du_check": "800_HOUR"}
]


class Project(TimeStampedModel):
    TIMESHEET_FREQUENCIES = (
        ('weekly', 'Weekly'),
        ('biweekly', 'Biweekly'),
        ('monthly', 'Monthly')
    )
    attachments = GenericRelation(Attachment)
    rate = models.FloatField(_('Rate'), null=True, blank=True)
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    feedback = models.TextField(_('Reason of Failure'), null=True, blank=True)
    support_required = models.BooleanField(_('Support Required'), default=True)
    payment_term = models.IntegerField(_('Payment Term'), null=True, blank=True)
    client_address = models.TextField(_('Client Address'), null=True, blank=True)
    vendor_address = models.TextField(_('Vendor Address'), null=True, blank=True)
    is_remote = models.BooleanField(_('Is Remote Project'), null=True, blank=True)
    employer = models.CharField(_('Employer'), max_length=50, null=True, blank=True)
    city = models.CharField(_('Client City'), max_length=100, blank=True, null=True)
    duration = models.CharField(_('Duration'), max_length=50, null=True, blank=True)
    reporting_details = models.TextField(_('Reporting Details'), null=True, blank=True)
    invoicing_period = models.IntegerField(_('Invoicing Period'), null=True, blank=True)
    timesheet_frequency = models.CharField(
        _("Frequency"), max_length=30,
        choices=TIMESHEET_FREQUENCIES, null=True, blank=True)
    is_msg_sent = models.BooleanField(
        _('Is Message Sent'),
        help_text='Message sent on Offer-announcement channel ?',
        default=False
    )
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

    @property
    def status(self):
        statuses = self.statuses.filter(is_current=True)
        if statuses:
            return statuses.first().get_status_display()
        return None


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
    is_proxy_support = models.BooleanField(_('Is Proxy Support'), default=False)
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
        ('updated', 'Updated'),
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
    rating = models.IntegerField(_('Consultant Rating'), null=True, blank=True)
    verdict = models.CharField(_('Consultant Verdict'), max_length=30, null=True, blank=True)
    department = models.CharField(_('Feedback Department'), max_length=30, null=True, blank=True)
    feedback_type = models.CharField(_('Feedback Type'), max_length=30, choices=FEEDBACK_CHOICES)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantFeedback, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name}:{self.feedback_type}'


class ConsultantLeave(TimeStampedModel):
    year = models.IntegerField(_('Year'))
    balance = models.FloatField(_('Balance Left'))
    granted = models.FloatField(_('Granted Leaves'))
    is_expired = models.BooleanField(_('Leave Expired'), default=False)
    leave_type = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='type')
    consultant = models.ForeignKey(
        Consultant, on_delete=models.PROTECT,
        related_name='leaves_balance', verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantLeave, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name}:{self.leave_type.name}'


class Leave(TimeStampedModel):
    LEAVE_STATUS = (
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applied', 'Pending 2nd Level'),
        ('pending', 'Pending 1st Level'),
        ('rejected_1st_level', 'Rejected 1st Level')
    )
    attachment = GenericRelation(Attachment)
    to_date = models.DateField(_("To Date"))
    from_date = models.DateField(_("From Date"))
    applied_on = models.DateField(_("Leave Apply Date"))
    remarks = models.TextField(_('Remark'), null=True, blank=True)
    description = models.TextField(_('Description'), null=True, blank=True)
    status = models.CharField(_('Status'), max_length=30, choices=LEAVE_STATUS)
    total_hours = models.FloatField(_('Total Hours'), max_length=30, null=True, blank=True)
    leave_type = models.ForeignKey(
        ConsultantLeave, on_delete=models.CASCADE,
        related_name='leaves', verbose_name='Leave'
    )
    consultant = models.ForeignKey(
        Consultant, null=True, blank=True,
        on_delete=models.PROTECT, related_name='leaves', verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Leave, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.leave_type.consultant.name}'


class TimesheetRequest(TimeStampedModel):
    TIMESHEET_REQUEST_STATUS = (
        ('reject', 'Reject'),
        ('request', 'Request'),
        ('accepted', 'Accepted'),
    )
    attachments = GenericRelation(Attachment)
    end = models.DateField(_('End'), null=True, blank=True)
    start = models.DateField(_('Start'), null=True, blank=True)
    status = models.CharField(_("Status"), max_length=30, choices=TIMESHEET_REQUEST_STATUS)
    reviewer_comment = models.TextField(_('Reviewer Comment'), null=True, blank=True)
    consultant_comment = models.TextField(_('Consultant Comment'), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='timesheet_req',
        verbose_name='Reviewed BY',
        null=True, blank=True
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='timesheet_requests',
        verbose_name='Project'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(TimesheetRequest, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.project.consultant.name} - {self.status}'


class TimetrackEvent(TimeStampedModel):
    FEEDBACK_TYPE = (
        ('external', 'External'),
        ('internal ', 'Internal'),
        ('feedback_not_required', 'Not Required')
    )
    end = models.DateField(_('End'), null=True, blank=True)
    start = models.DateField(_('Start'), null=True, blank=True)
    is_active = models.BooleanField(_('Is active'), default=True)
    description = models.TextField(_('description'), null=True, blank=True)
    action_link = models.TextField(_('action_link'), null=True, blank=True)
    title = models.CharField(_('title'), max_length=80, null=True, blank=True)
    feedback_type = models.CharField(_("Status"), max_length=30, choices=FEEDBACK_TYPE)
    event_type = models.CharField(_('event_type'), max_length=30, null=True, blank=True)
    image = models.ImageField(_("event Picture"), upload_to='timesheet_event/', blank=True, null=True)
    consultants = models.ManyToManyField(Consultant, related_name='events', verbose_name='consultant')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='campaign', verbose_name='user')


class TimetrackEventFeedback(models.Model):
    feedback = models.TextField(_('feedback'), null=True, blank=True)
    consultant = models.ForeignKey(
        Consultant, on_delete=models.PROTECT,
        related_name='event',
        verbose_name='consultant'
    )
    event = models.ForeignKey(
        TimetrackEvent, on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name='event'
    )


class ProjectPaymentTerm(TimeStampedModel):
    PAYMENT_TERM_TYPE = (
        ('on_net_pay', 'On Net Pay'),
        ('on_gross_pay', 'On Gross Pay'),
        ('100%_to_company', '100% To Company'),
        ('100%_to_consultant', '100% To Consultant')
    )
    comment = models.TextField(_("Comment"), null=True, blank=True)
    term_end = models.DateTimeField(_("Term_End"), null=True, blank=True)
    payment_term = models.FloatField(_('Company Payment Term'), null=True, blank=True)
    consultant_payment_term = models.FloatField(_('Consultant Payment Term'), null=True, blank=True)
    payment_term_type = models.CharField(_("Payment_Term_Type"), max_length=30, choices=PAYMENT_TERM_TYPE)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT,
        related_name='project_payment_term',
        verbose_name='Project',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Created By',
        related_name='project_payment',
    )

    def __str__(self):
        return self.payment_term_type


class ProjectAssociates(TimeStampedModel):
    notification_type = models.JSONField(null=True)
    total_hours = models.FloatField(_("Total Hours"))
    initial_notification = models.BooleanField(_("Notification For 160 hrs"), default=False)
    secondary_notification = models.BooleanField(_("Notification For 1000 hrs"), default=False)
    vp = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='VP', related_name='vp')
    interviews = models.ManyToManyField(Interview, verbose_name='Interview', related_name='project_interviews')
    project = models.OneToOneField(Project, on_delete=models.PROTECT, verbose_name='Project', related_name='associate')
    lead_sm = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Lead SM',
        related_name='lead_sm',
        null=True, blank=True
    )
    team_lead = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='team_projects',
        verbose_name='Team Lead',
        null=True, blank=True
    )
    marketer = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='marketed_consultants',
        verbose_name='Marketer'
    )
    recruiter = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='recruited_consultants',
        verbose_name='Recruiter',
        null=True, blank=True,
    )
    support_persons = models.ManyToManyField(
        ProjectSupport,
        null=True, blank=True,
        verbose_name='Support Person',
        related_name='supported_projects'
    )

    def __str__(self):
        return f"{self.project.consultant.name}-{self.project.submission.client}"
