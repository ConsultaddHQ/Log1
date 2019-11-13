from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from employee.models import User
from attachment.models import Attachment
from utils_app.models import TimeStampedModel
from consultant.models import ConsultantMarketing

STATUS_CHOICES = (
    ('new', 'New'),
    ('draft', 'Draft'),
    ('sub', 'Submitted'),
    ('archived', 'Archived'),
)

SUB_CHOICES = (
    ('draft', 'Draft'),
    ('sub', 'Submitted'),
    ('project', 'Project'),
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

SCREENING_CHOICES = (
    ('skype', 'Skype'),
    ('webex', 'Webex'),
    ('hangout', 'Hangout'),
    ('video_call', 'Video Call'),
    ('telephonic', 'Voice Call'),
    ('telephonic-conf', 'Voice Conference Call'),
)


class VendorCompany(models.Model):
    name = models.CharField(_('Company'), max_length=50)
    created_by = models.CharField(_('Created By'), max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Vendor Company")
        verbose_name_plural = _("Vendor Companies")


class VendorContact(TimeStampedModel):
    name = models.CharField(_('Name'), max_length=50)
    email = models.EmailField(_('Email'), max_length=50, null=True, blank=True)
    number = models.CharField(_('Number'), max_length=25, null=True, blank=True)
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
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(VendorContact, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} from {self.company}'


class Lead(TimeStampedModel):
    job_desc = models.TextField(_('Job Description'))
    city = models.CharField(_('City'), max_length=50, blank=True, null=True)
    job_title = models.CharField(_('Job Title'), max_length=100, blank=True, null=True)
    primary_skill = models.CharField(_('Primary Skill'), max_length=50, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='new')
    secondary_skills = ArrayField(models.CharField(_('Secondary Skills'), max_length=30, blank=True, null=True))
    vendor_company = models.ForeignKey(
        VendorCompany, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='leads',
        verbose_name='Vendor Company'
    )
    marketer = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='leads',
        verbose_name='Marketer'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Lead, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.vendor_company} : {self.city} : {self.marketer.employee_name}'


class Submission(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    employer = models.CharField(_('Employer'), max_length=50)
    rate = models.FloatField(_('Rate'), null=True, blank=True)
    is_active = models.BooleanField(_('Is active'), default=False)
    email = models.EmailField(_('Marketing Email'), null=True, blank=True)
    client = models.CharField(_('Client'), max_length=50, null=True, blank=True)
    phone = models.CharField(_('Marketing Phone'), max_length=20, null=True, blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=SUB_CHOICES, default='sub')

    # Consultant Profile
    education = models.TextField(_('Academics Details'))
    visa_end = models.DateField(_('Visa End Date'), blank=True, null=True)
    visa_start = models.DateField(_('Visa Start Date'), blank=True, null=True)
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

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Submission, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.lead.marketer.employee_name} : {self.client}'


class VendorLayer(TimeStampedModel):
    level = models.IntegerField()
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
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(VendorLayer, self).save(*args, **kwargs)

    def __str__(self):
        return f'Level: {self.level} {self.vendor_company.name}'


class Interview(TimeStampedModel):
    round = models.IntegerField(default=0)
    feedback = models.TextField(_('Feedback'), null=True, blank=True)
    end_time = models.DateTimeField(_('End Date'), null=True, blank=True)
    description = models.TextField(_('Description'), null=True, blank=True)
    start_time = models.DateTimeField(_('Start Date'), null=True, blank=True)
    call_details = models.TextField(_('Call Details'), null=True, blank=True)
    attachment_link = models.TextField(_('Attachment Links'), null=True, blank=True)
    calendar_id = models.CharField(_('Calendar ID'), max_length=50, null=True, blank=True)
    interview_type = models.CharField(_('Interview Type'), max_length=20, choices=SCREENING_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=SCREENING_STATUS_CHOICES, default='scheduled')
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
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Interview, self).save(*args, **kwargs)

    def __str__(self):
        if self.start_time:
            return f'CTB:{self.supervisor} :: {self.round}R :: {self.get_interview_type_display()} :: ' \
                   f'{self.start_time.strftime("%d/%m/%Y::%I:%M %p EST")} :: {self.submission.client} :: ' \
                   f' {self.submission.consultant.name} :: {self.submission.lead.marketer.employee_name}'
