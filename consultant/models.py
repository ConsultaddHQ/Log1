import os
import binascii
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.contenttypes.fields import GenericRelation

from activity.models import Comment
from employee.models import User, Team
from utils_app.mailing import send_email
from attachment.models import Attachment
from utils_app.models import TimeStampedModel
from employee.token import get_token_generator
from notification.models import FCMDevice, Notification

CONSULTANT_STATUS_CHOICE = (
    ('on_bench', 'On Bench'),
    ('archived', 'Archived'),
    ('on_project', 'On Project'),
)

MARKETING_STATUS_CHOICE = (
    ('open', 'Open'),
    ('close', 'Close'),
)

VISA_CHOICES = (
    ('tps', 'TPs'),
    ('h1b', 'H1B'),
    ('other', 'Other'),
    ('gc_ead', 'GC EAD'),
    ('cpt-ead', 'CPT EAD'),
    ('gc', 'Green Card Holder'),
    ('opt-ext', 'OPT Extension'),
    ('us_citizen', 'US CITIZEN'),
    ('not_auth', 'Not Authorized'),
    ('gc:ead', 'Green Card Holder EAD'),
)

EDUCATION_CHOICES = (
    ('diploma', 'Diploma'),
    ('masters', 'Masters'),
    ('bachelors', 'Bachelors'),
    ('certification', 'Certification'),
)

FEEDBACK_CHOICES = (
    ('training', 'Training'),
    ('screening', 'Screening'),
    ('pre_joining', 'Pre Joining'),
    ('re_marketing', 'Re Marketing'),
    ('rate_revision', 'Rate Revision'),
)

GENDER_CHOICE = (
    ('male', 'Male'),
    ('female', 'Female'),
)

WORK_TYPE_CHOICE = (
    ('c2c', 'C2C'),
    ('full_time', 'Full Time'),
)

TOKEN_GENERATOR_CLASS = get_token_generator()


class ConsultantManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})


class Consultant(AbstractBaseUser, TimeStampedModel):
    is_active = models.BooleanField(default=False)
    first_login = models.BooleanField(default=True)
    email = models.EmailField(_('Email ID'), unique=True)
    name = models.CharField(_('Full Name'), max_length=100)
    comments = GenericRelation(Comment, verbose_name="comments")
    attachments = GenericRelation(Attachment, verbose_name="Documents")
    ssn = models.CharField(_('SSN ID'), max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(_('Date of birth'), blank=True, null=True)
    links = models.CharField(_('Links'), max_length=100, blank=True, null=True)
    skills = models.CharField(_('Skills'), max_length=100, null=True, blank=True)
    skype = models.CharField(_('Skype Id'), max_length=100, null=True, blank=True)
    phone_no = models.CharField(_('Phone Number'), max_length=20, null=True, blank=True)
    current_city = models.CharField(_('Current City'), max_length=100, blank=True, null=True)
    gender = models.CharField(
        _('Gender'), max_length=10,
        choices=GENDER_CHOICE,
        null=True, blank=True
    )
    status = models.CharField(
        _('status'), max_length=15,
        choices=CONSULTANT_STATUS_CHOICE,
        default='on_bench'
    )
    work_type = models.CharField(
        _('Work Type'), max_length=10,
        choices=WORK_TYPE_CHOICE,
        default='full_time'
    )

    objects = ConsultantManager()

    USERNAME_FIELD = 'email'

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Consultant, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.name} {self.email}'

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})

    def get_project(self):
        from project.models import Project
        queryset = Project.objects.filter(
            models.Q(consultant=self)
        )
        return queryset

    @property
    def get_attachment(self):
        return self.attachments.all()

    @property
    def recruiter(self):
        queryset = self.pocs.filter(poc_type='recruiter', end=None)
        if queryset:
            return queryset.first().poc
        return None

    @property
    def relation(self):
        queryset = self.pocs.filter(poc_type='relation', end=None)
        if queryset:
            return queryset.first().poc
        return None

    @property
    def rate(self):
        queryset = self.rates.filter(end=None)
        if queryset:
            return queryset.first().rate
        return None

    @staticmethod
    def send_mail(mail_data):
        try:
            res = send_email(mail_data, "admin@consultadd.com")
            return res, "ok"
        except Exception as error:
            return error, "error"


class ConsultantResetPasswordToken(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)
    user_agent = models.CharField(_("HTTP User Agent"), max_length=256, default="")
    consultant = models.ForeignKey(Consultant, related_name='password_reset_tokens', on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("The IP address of this session"), default="127.0.0.1")

    class Meta:
        verbose_name = _("Consultant Password Reset Token")
        verbose_name_plural = _("Consultant Password Reset Tokens")

    @staticmethod
    def generate_key():
        return TOKEN_GENERATOR_CLASS.generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConsultantResetPasswordToken, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant}-{self.key}'


def clear_expired(expiry_time):
    ConsultantResetPasswordToken.objects.filter(created_at__lte=expiry_time).delete()


class ConsultantToken(models.Model):
    """
    The default authorization token model.
    """
    fcm_tokens = GenericRelation(FCMDevice)
    key = models.CharField(_("Key"), max_length=40, primary_key=True)
    uuid = models.CharField(_("Universally Unique Identifier"), max_length=64, db_index=True, default='UUID')
    consultant = models.OneToOneField(
        Consultant, related_name='consultant_token',
        on_delete=models.CASCADE, verbose_name=_("Consultant")
    )
    created = models.DateTimeField(_("Created"), auto_now_add=True)

    class Meta:
        verbose_name = _("Consultant Token")
        verbose_name_plural = _("Consultant Tokens")

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConsultantToken, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key


class WorkAuth(TimeStampedModel):
    is_current = models.BooleanField(_('Is current Visa'), default=True)
    visa_end = models.DateField(_('Visa End Date'), blank=True, null=True)
    visa_start = models.DateField(_('Visa Start Date'), blank=True, null=True)
    visa_type = models.CharField(_('Visa Type'), max_length=20, choices=VISA_CHOICES, blank=True, null=True)
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='work_auth',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(WorkAuth, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name} {self.visa_start}'


class Education(models.Model):
    title = models.CharField(_('Education Title'), max_length=300)
    remark = models.TextField(_('Additional Details'), null=True, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True, null=True)
    major = models.CharField(_('Field of Study'), max_length=50, null=True, blank=True)
    org_name = models.CharField(_('Organization Name'), max_length=50, null=True, blank=True)
    edu_type = models.CharField(_('Education Type'), max_length=50, choices=EDUCATION_CHOICES, null=True, blank=True)
    start_date = models.DateField(
        _('Start Date'),
        null=True, blank=True,
        help_text='Month and Year Of Start'
    )
    end_date = models.DateField(
        _('End Date'),
        null=True, blank=True,
        help_text='Month and Year of End'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='academics',
        verbose_name='Consultant'
    )


class Experience(models.Model):
    title = models.CharField(_('Title'), max_length=300)
    remark = models.TextField(_('Additional Details'), null=True, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True, null=True)
    company = models.CharField(_('Company name'), max_length=100, null=True, blank=True)
    exp_type = models.CharField(_('Experience Type'), max_length=50, null=True, blank=True)
    start_date = models.DateField(
        _('Start Date'),
        null=True, blank=True,
        help_text='Month and Year Of Start'
    )
    end_date = models.DateField(
        _('End Date'),
        null=True, blank=True,
        help_text='Month and Year of End'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='experiences',
        verbose_name='Consultant'
    )


class ConsultantProfile(TimeStampedModel):
    title = models.CharField(max_length=200, blank=True, null=True)
    visa_end = models.DateField(_('Visa End Date'), blank=True, null=True)
    visa_start = models.DateField(_('Visa Start Date'), blank=True, null=True)
    education = models.TextField(_('Academics Details'), blank=True, null=True)
    date_of_birth = models.DateField(_('Date of birth'), blank=True, null=True)
    links = models.CharField(_('Links'), max_length=100, blank=True, null=True)
    visa_type = models.CharField(_('Visa Type'), max_length=20, blank=True, null=True)
    linkedin = models.CharField(_('Linkedin URL'), max_length=300, blank=True, null=True)
    current_city = models.CharField(_('Current City'), max_length=100, blank=True, null=True)
    profile_owner = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='profiles',
        verbose_name='Profile Owner'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='profiles',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantProfile, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.title}-{self.consultant.name}'


class ConsultantMarketing(TimeStampedModel):
    rtg = models.BooleanField(_('Ready to Go'), default=False)
    cycle = models.IntegerField(_('Cycle Number'), default=1)
    in_pool = models.BooleanField(_('In Pool'), default=False)
    end = models.DateField(_('Marketing End Date'), blank=True, null=True)
    start = models.DateField(_('Marketing Start Date'), blank=True, null=True)
    preferred_location = models.TextField(_('Preferred Location'), null=True, blank=True)
    status = models.CharField(
        _('status'), max_length=10,
        choices=MARKETING_STATUS_CHOICE,
        default='open'
    )
    teams = models.ManyToManyField(
        Team,
        related_name='consultants',
        verbose_name='Teams'
    )
    marketer = models.ManyToManyField(
        User,
        blank=True,
        related_name='marketed',
        verbose_name='Marketer Assigned'
    )
    primary_marketer = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='primary_consultant',
        verbose_name='Primary Marketer'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='marketing',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantMarketing, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.cycle}-{self.consultant.name}'

    @property
    def recruiter(self):
        return self.consultant.recruiter

    @property
    def relation(self):
        return self.consultant.relation


class ConsultantRateRevision(TimeStampedModel):
    rate = models.FloatField(_('Rate'))
    previous_rate = models.IntegerField(_('Previous Rate'), default=0)
    start = models.DateField(_('Rate Start Date'), blank=True, null=True)
    feedback = models.TextField(_('Revision Feedback'), blank=True, null=True)
    end = models.DateField(_('Rate End Date'), default=None, blank=True, null=True)
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='rates',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantRateRevision, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name}-{self.rate}-{self.start}'


class ConsultantPOC(TimeStampedModel):
    start = models.DateField(_('Rate Start Date'), blank=True, null=True)
    end = models.DateField(_('Rate End Date'), default=None, blank=True, null=True)
    poc_type = models.CharField(_('Recruiter Or Retention'), max_length=20, blank=True, null=True)
    poc = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='consultants',
        verbose_name='Point of Contact'
    )
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='pocs',
        verbose_name='Consultant'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantPOC, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}-{self.poc.employee_name} {self.poc_type} of {self.consultant.name}'


class FeedbackDetail(models.Model):
    experience = models.TextField(_('Experience'), blank=True, null=True)
    role_knowledge = models.TextField(_('Role Knowledge'), blank=True, null=True)
    programming = models.TextField(_('Programming Skill'), blank=True, null=True)
    communication = models.TextField(_('Communication Skills'), blank=True, null=True)
    problem_solving = models.TextField(_('Problem Solving Skill'), blank=True, null=True)
    organizational = models.TextField(_('Organizational Knowledge'), blank=True, null=True)

    def __str__(self):
        return self.id


class ConsultantFeedback(TimeStampedModel):
    remark = models.TextField(_('Remark'), null=True, blank=True)
    feedback_type = models.CharField(
        _('Feedback Type'), max_length=20,
        choices=FEEDBACK_CHOICES,
    )
    rating = models.IntegerField(
        _('Consultant Rating'),
        help_text=_('Rating 1 being worst and 5 being best')
    )
    feedback = models.ForeignKey(
        FeedbackDetail, on_delete=models.CASCADE,
        related_name='consultant',
        verbose_name='Consultant Feedback')
    consultant = models.ForeignKey(
        Consultant, on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name='Consultant'
    )
    given_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='feedback_given',
        verbose_name='Feedback given by'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='feedback_created',
        verbose_name='Feedback added by'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ConsultantFeedback, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}:{self.consultant.name} {self.feedback_type} of {self.rating}'
