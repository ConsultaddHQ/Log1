from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from activity.models import Comment
from employee.models import User, Team
from attachment.models import Attachment
from utils_app.models import TimeStampedModel

CONSULTANT_STATUS_CHOICE = (
    ('archived', 'Archived'),
    ('in_offer', 'In Offer'),
    ('on_project', 'On Project'),
    ('terminated', 'Terminated'),
    ('in_training', 'In Training'),
    ('in_marketing', 'In Marketing'),
    ('marketing_candidate', 'Marketing Candidate'),
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
    ('gc-ead', 'Green Card Holder EAD'),
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
    ('female', 'Female')
)

WORK_TYPE_CHOICE = (
    ('c2c', 'C2C'),
    ('full_time', 'Full Time')
)


class Consultant(TimeStampedModel):
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
        default='in_marketing'
    )
    work_type = models.CharField(
        _('Work Type'), max_length=10,
        choices=WORK_TYPE_CHOICE,
        default='full_time'
    )

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Consultant, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} {self.email}'

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
        return f'{self.consultant.name} {self.visa_start}'


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
        return f'{self.title} - {self.consultant.name}'


class ConsultantMarketing(TimeStampedModel):
    rtg = models.BooleanField(_('Ready to Go'), default=False)
    cycle = models.IntegerField(_('Cycle Number'), default=1)
    in_pool = models.BooleanField(_('In Pool'), default=False)
    end = models.DateField(_('Marketing End Date'), blank=True, null=True)
    start = models.DateField(_('Marketing Start Date'), blank=True, null=True)
    preferred_location = models.TextField(_('Preferred Location'), null=True, blank=True)
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
        return f'{self.cycle} - {self.consultant.name}'

    @property
    def recruiter(self):
        return self.consultant.recruiter

    @property
    def relation(self):
        return self.consultant.relation


class ConsultantRateRevision(TimeStampedModel):
    rate = models.IntegerField(_('Rate'))
    previous_rate = models.IntegerField(_('Previous Rate'), default=0)
    end = models.DateField(_('Rate End Date'), blank=True, null=True)
    start = models.DateField(_('Rate Start Date'), blank=True, null=True)
    feedback = models.TextField(_('Revision Feedback'), blank=True, null=True)
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
        return f'{self.consultant.name} - {self.rate} - {self.start}'


class ConsultantPOC(TimeStampedModel):
    end = models.DateField(_('Rate End Date'), blank=True, null=True)
    start = models.DateField(_('Rate Start Date'), blank=True, null=True)
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
        return f'{self.poc.employee_name} {self.poc_type} of {self.consultant.name}'


class FeedbackDetail(models.Model):
    role = models.TextField(_('Role Knowledge'), blank=True, null=True)
    experience = models.TextField(_('Experience'), blank=True, null=True)
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
        return f'{self.consultant.name} {self.feedback_type} of {self.rating}'
