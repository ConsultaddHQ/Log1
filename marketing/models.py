from django.db import models
from django.utils import timezone
from django.contrib.auth.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey

from employee.models import User
from activity.models import Comment
from attachment.models import Attachment
from consultant.models import ConsultantMarketing
from utils_app.models import TimeStampedModel, Choice

STATUS_CHOICES = (
    ('new', 'New'),
    ('draft', 'Draft'),
    ('sub', 'Submitted'),
    ('archived', 'Archived'),
)

TEST_STATUS_CHOICES = (
    ('new', 'New'),
    ('passed', 'Passed'),
    ('failed', 'Failed'),
    ('assigned', 'Assigned'),
    ('cancelled', 'Cancelled'),
    ('feedback_due', 'Feedback Due'),
)

SUB_CHOICES = (
    ('draft', 'Draft'),
    ('sub', 'Submitted'),
    ('project', 'Project'),
    ('in_offer', 'In Offer'),
    ('interview', 'Interview'),
)

STAGES_CHOICE = (
    ('open', 'Open'),
    ('close', 'Close'),
)

SCREENING_STATUS_CHOICES = (
    ('offer', 'offer'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
    ('scheduled', 'Scheduled'),
    ('next_round', 'Next Round'),
    ('rescheduled', 'Rescheduled'),
    ('feedback_due', 'Feedback Due'),
)

INTERVIEW_MODE = (
    ('skype', 'Skype'),
    ('webex', 'Webex'),
    ('dial_in', 'Dial In'),
    ('hangouts', 'Hangout'),
    ('video_call', 'Video Call'),
    ('voice_call', 'Voice Call'),
)

SCREENING_CHOICES = (
    ('ip_screening', 'IP Tech Screening'),
    ('vendor_screening', 'Vendor Tech Screening'),
    ('interview', 'Interview'),
)

FAILURE_CHOICES = (
    ('resume_error', 'Error In Resume'),
    ('hired_else', 'Hired Someone Else'),
    ('internal_hiring', 'Internal Hiring'),
    ('system_updated', 'System Auto Update'),
    ('caught_mimicking', 'Caught us Mimicking'),
    ('insufficient_skills', 'Insufficient Skills'),
    ('test_failed', 'Test Failed during Interview'),
    ('feedback_not_received', 'Never Received Feedback'),
    ('irresponsible_behaviour', "Candidate's Irresponsible Behaviour"),
    ('lack_of_coordination', 'Lack of Coordination Between Coder and Interviewee'),
    ('call_attempted_by_inexperienced', 'Call Attempted by Someone with Less Experience'),
)


class VendorCompany(models.Model):
    name = models.CharField(_('Company'), max_length=100)
    created_by = models.CharField(_('Created By'), max_length=50, null=True, blank=True)

    def __str__(self):
        return f'{self.id}:{self.name}'

    class Meta:
        verbose_name = _("Vendor Company")
        verbose_name_plural = _("Vendor Companies")


class VendorContact(TimeStampedModel):
    name = models.CharField(_('Name'), max_length=50)
    email = models.EmailField(_('Email'), max_length=100, null=True, blank=True)
    number = models.CharField(_('Number'), max_length=100, null=True, blank=True)
    company = models.ForeignKey(
        VendorCompany, on_delete=models.CASCADE,
        related_name='vendors',
        null=True, blank=True,
        verbose_name='Vendor Company'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='vendors',
        null=True, blank=True,
        verbose_name='Vendor Contact Created By'
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(VendorContact, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.name} from {self.company}'


class Lead(TimeStampedModel):
    is_w2 = models.BooleanField(default=False)
    job_desc = models.TextField(_('Job Description'))
    city = models.CharField(_('City'), max_length=50, blank=True, null=True)
    job_title = models.CharField(_('Job Title'), max_length=100, blank=True, null=True)
    primary_skill = models.CharField(_('Primary Skill'), max_length=50, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='new')
    secondary_skills = ArrayField(models.CharField(_('Secondary Skills'), max_length=30), blank=True, null=True)

    position = models.ForeignKey(
        Choice, on_delete=models.SET_NULL,
        related_name='position_lead',
        null=True, blank=True
    )
    vendor_company = models.ForeignKey(
        VendorCompany, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='leads',
        verbose_name='Vendor Company'
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='leads',
        verbose_name='Lead Owner'
    )
    shared_to = models.ManyToManyField(
        User, blank=True,
        related_name='shared_leads',
        verbose_name='Lead Shared to',
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Lead, self).save(*args, **kwargs)

    def __str__(self):
        if self.owner and self.vendor_company:
            return f'{self.id}:{self.vendor_company.name} - {self.owner.employee_name} - {self.city}'
        return f'{self.id}- {self.city}'


class Submission(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    rank = models.IntegerField(_('Rank'), default=0)
    employer = models.CharField(_('Employer'), max_length=50)
    rate = models.FloatField(_('Rate'), null=True, blank=True)
    comments = GenericRelation(Comment, verbose_name="comments")
    is_active = models.BooleanField(_('Is active'), default=False)
    is_complete = models.BooleanField(_('Is complete'), default=False)
    email = models.EmailField(_('Marketing Email'), null=True, blank=True)
    client = models.CharField(_('Client'), max_length=100, null=True, blank=True)
    phone = models.CharField(_('Marketing Phone'), max_length=30, null=True, blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=SUB_CHOICES, default='sub')

    # Consultant Profile
    visa_end = models.DateField(_('Visa End Date'), blank=True, null=True)
    visa_start = models.DateField(_('Visa Start Date'), blank=True, null=True)
    education = models.TextField(_('Academics Details'), blank=True, null=True)
    visa_type = models.CharField(_('Visa Type'), max_length=20, blank=True, null=True)
    linkedin = models.CharField(_('Linkedin URL'), max_length=300, blank=True, null=True)
    other_link = models.CharField(_('Other Links'), max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(_('Consultant date of birth'), blank=True, null=True)
    current_city = models.CharField(_('Current City'), max_length=100, blank=True, null=True)

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        related_name='submission',
        verbose_name='Lead'
    )
    consultant_marketing = models.ForeignKey(
        ConsultantMarketing, on_delete=models.PROTECT,
        related_name='submissions',
        verbose_name='Consultant '
    )
    vendor_contact = models.ForeignKey(
        VendorContact, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='submissions',
        verbose_name='Vendor Contact'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='submissions',
        verbose_name='Submission done by'
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Submission, self).save(*args, **kwargs)

    def __str__(self):
        if self.created_by:
            return f'{self.id}:{self.created_by.employee_name} - {self.client}'
        return f'{self.id}:{self.client}'

    @property
    def consultant(self):
        return self.consultant_marketing.consultant

    @property
    def lead_owner(self):
        return self.lead.owner

    @property
    def vendor(self):
        return self.lead.vendor_company


class VendorLayer(TimeStampedModel):
    level = models.IntegerField(default=1)
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        related_name='vendors',
        verbose_name='Submission'
    )
    vendor_company = models.ForeignKey(
        VendorCompany, on_delete=models.CASCADE,
        related_name='vendor_layers',
        verbose_name='Company'
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(VendorLayer, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:L{self.level} {self.vendor_company.name}'


class Question(TimeStampedModel):
    TYPE = (
        ('text', 'Text'),
        ('rate', 'Rate'),
        ('option', 'Option'),
        ('boolean', 'Boolean'),
        ('integer', 'Integer'),
        ('long_text', 'Long Text'),
        ('attachment', 'Attachment'),
    )
    value = models.TextField(_('Question Value'))
    field = models.CharField(_('Model Field'), max_length=100, null=True, blank=True)
    options = ArrayField(models.CharField(_('Choices'), max_length=30, blank=True), blank=True)

    category = models.CharField(_('Question Category'), max_length=50)
    answer_type = models.CharField(_('Type'), max_length=20, choices=TYPE)
    position = models.PositiveIntegerField(_('Position'), null=True, blank=True)

    def __str__(self):
        return f'{self.field} - {self.answer_type} - {self.category}'

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Question, self).save(*args, **kwargs)


class Answer(TimeStampedModel):
    attachment = GenericRelation(Attachment)
    value = models.TextField(_('Value'), null=True, blank=True)
    remark = models.TextField(_('Remark'), null=True, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer')

    object_id = models.PositiveIntegerField(_('Object Id'), )
    content_object = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        ordering = ('-modified',)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Answer, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.question.value}'


class Test(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    engineer_feedback = GenericRelation(Answer)
    link = models.TextField(_('Test Link'), null=True, blank=True)
    is_video = models.BooleanField(_('Video Test'), default=False)
    is_offline = models.BooleanField(_('Offline Test'), default=False)
    feedback = models.TextField(_('Test Feedback'), null=True, blank=True)
    deadline = models.DateField(_('Test Deadline'), null=True, blank=True)
    cancel_reason = models.TextField(_('Cancellation Reason'), null=True, blank=True)
    engineer_remarks = models.TextField(_("Engineer Remarks"), null=True, blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=TEST_STATUS_CHOICES)
    submit_date = models.DateTimeField(_('Test Submission Date'), null=True, blank=True)
    additional_details = models.TextField(_('Additional Details'), null=True, blank=True)
    skills = ArrayField(models.CharField(_('Skills'), max_length=30), blank=True, null=True)
    engineer = models.ManyToManyField(
        User,
        blank=True,
        related_name='associated_tests',
        verbose_name='Engineer Associated'
    )
    assign_to = models.ManyToManyField(
        User,
        related_name='test_assigned',
        verbose_name='Test assigned to'
    )
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        related_name='test',
        verbose_name='Submission'
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='test_submissions',
        verbose_name='Submission done by'
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Test, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission.consultant.name} :: {self.submission.created_by.employee_name}"

    @property
    def marketer(self):
        return self.submission.created_by


class Interview(TimeStampedModel):
    round = models.IntegerField(default=0)
    feedback = models.TextField(_('Feedback'), null=True, blank=True)
    guest_remark = models.TextField(_('Remark'), blank=True, null=True)
    coding_present = models.BooleanField(_('Coding Present'), null=True)
    end_time = models.DateTimeField(_('End Date'), null=True, blank=True)
    notes = models.TextField(_('Interview Notes'), null=True, blank=True)
    description = models.TextField(_('Description'), null=True, blank=True)
    guest_type = models.CharField(_('Guest Type'), max_length=50, null=True)
    start_time = models.DateTimeField(_('Start Date'), null=True, blank=True)
    call_details = models.TextField(_('Call Details'), null=True, blank=True)
    tech_stack = models.TextField(_('Technology required'), null=True, blank=True)
    attachment_link = models.TextField(_('Attachment Links'), null=True, blank=True)
    calendar_id = models.CharField(_('Calendar ID'), max_length=300, null=True, blank=True)
    interview_mode = models.CharField(_('Interview Mode'), max_length=20, choices=INTERVIEW_MODE)
    screening_type = models.CharField(_('Screening Type'), max_length=20, choices=SCREENING_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=SCREENING_STATUS_CHOICES, default='scheduled')
    failure_reason = ArrayField(models.CharField(
        _('Failure Reason'),
        max_length=50, choices=FAILURE_CHOICES),
        null=True, blank=True
    )
    supervisor = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='screening',
        verbose_name='Supervisor'
    )
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        related_name='screening',
        verbose_name='Submission'
    )
    guest = models.ManyToManyField(
        User, related_name='screenings',
        verbose_name='Guest',
        blank=True
    )

    def save(self, *args, **kwargs):

        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Interview, self).save(*args, **kwargs)

    def __str__(self):
        if self.start_time:
            return f'''CTB:{self.supervisor} :: {self.round}R :: {self.get_screening_type_display()} ::
                   {self.start_time.strftime("%d/%m/%Y::%I:%M %p EST")} :: {self.submission.client} ::
                   {self.submission.consultant.name} :: {self.submission.created_by.employee_name}'''

    @property
    def marketer(self):
        return self.submission.created_by

    @property
    def consultant(self):
        return self.submission.consultant_marketing.consultant
