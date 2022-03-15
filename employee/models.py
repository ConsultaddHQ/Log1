from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import AbstractUser, PermissionsMixin

from api_key.models import APIKey
from log1.utils import write_exception
from utils_app.mailing import send_email
from utils_app.models import TimeStampedModel
from employee.token import get_token_generator


TOKEN_GENERATOR_CLASS = get_token_generator()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, employee_id, email, name, team=None, gender=None, phone=None, password=None):
        """
            Create and save a user with the given Employee_id, email, name, and password.
        """
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(
            team=team,
            email=email,
            phone=phone,
            gender=gender,
            employee_name=name,
            username=int(employee_id),
            employee_id=int(employee_id),
        )

        user.set_password(password)
        user.is_active = True
        user.save()
        return user

    def create_superuser(self, employee_id, password):
        """
            Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            employee_id,
            "admin@consultadd.com",
            "Admin",
            password=password
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Team(models.Model):
    name = models.CharField(_('Name'), max_length=50)
    email = models.EmailField(_('Email'), null=True, blank=True)
    dept = models.CharField(_('Department'), max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(_('Role Name'), max_length=50)

    def __str__(self):
        return self.name


class User(AbstractUser, PermissionsMixin):
    """
    Custom employee realization based on Django AbstractUser and PermissionMixin.
    """
    GENDER_CHOICE = (
        ('male', 'Male'),
        ('female', 'Female')
    )
    email = models.EmailField(_('Email'))
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    account_login = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    role = models.ManyToManyField(Role, related_name='roles')
    employee_id = models.IntegerField(_('Employee ID'), unique=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    employee_name = models.CharField(_("Full Name"), max_length=100, blank=True)
    phone = models.CharField(_("Phone Number"), max_length=20, null=True, blank=True)
    avatar = models.ImageField(_("Profile Picture"), upload_to='avatar/', blank=True, null=True)
    technology = ArrayField(models.CharField(_('Technologies'), max_length=30, blank=True), blank=True)
    gender = models.CharField(_('Gender'), choices=GENDER_CHOICE, max_length=10, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='employees', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = []

    class Meta:
        app_label = 'employee'
        ordering = ('employee_name',)

    def __str__(self):
        return f'{self.employee_name}-{self.email}'

    @property
    def roles(self):
        return [role.name for role in self.role.all()]

    @property
    def consultant(self):
        if 'consultant' in self.roles:
            from consultant.models import Consultant
            consultant = Consultant.objects.filter(email=self.email)
            if consultant:
                return consultant.first()
        return None

    def send_mail(self, mail_data):
        try:
            res, msg = send_email(mail_data, "admin@consultadd.com")
            if not msg:
                return res, "error"
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, "error"

    def save(self, *args, **kwargs):
        if not self.id and self.employee_name:
            self.first_name = self.employee_name.split()[0]
            self.last_name = self.employee_name.split()[1] if len(self.employee_name.split()) > 1 else ""
        return super(User, self).save(*args, **kwargs)


class ResetPasswordToken(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)
    user_agent = models.CharField(_("HTTP User Agent"), max_length=256, default="")
    user = models.ForeignKey(User, related_name='password_reset_tokens', on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("The IP address of this session"), default="127.0.0.1")

    class Meta:
        verbose_name = _("Password Reset Token")
        verbose_name_plural = _("Password Reset Tokens")

    @staticmethod
    def generate_key():
        return TOKEN_GENERATOR_CLASS.generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ResetPasswordToken, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.user}-{self.key}'


def get_token_expiry_time():
    return getattr(settings, 'RESET_TOKEN_EXPIRY_TIME', 24)


def clear_expired(expiry_time):
    ResetPasswordToken.objects.filter(created_at__lte=expiry_time).delete()


class Asset(TimeStampedModel):
    ASSET_TYPES = (
        ('email', 'Email'),
        ('social', 'Social'),
        ('number', 'Number'),
        ('job_board', 'Job Board')
    )
    username = models.CharField(_('Username'), max_length=50)
    provider = models.CharField(_('Provider'), max_length=30)
    password = models.CharField(_('Password'), max_length=50)
    email = models.EmailField(_('Email'), max_length=50, null=True, blank=True)
    is_deleted = models.BooleanField(_('Is Deleted'), default=False)
    alter_email = models.EmailField(_('Alternate Email'), max_length=50, null=True, blank=True)
    number = models.CharField(_('Number'), max_length=50, null=True, blank=True)
    tech = models.CharField(_('Technology'), max_length=40, null=True, blank=True)
    remarks = models.CharField(_('Remarks'), max_length=300, null=True, blank=True)
    alter_number = models.CharField(_('Alternate Number'), max_length=40, null=True, blank=True)
    asset_type = models.CharField(_('Asset Type'), choices=ASSET_TYPES, max_length=20, null=True, blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name=_('assets'),
        verbose_name='Asset Owner'
    )
    shared_to = models.ManyToManyField(
        User,
        related_name='shared_assets',
        verbose_name='Asset shared with'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Asset, self).save(*args, **kwargs)

    def __str__(self):
        return self.owner.employee_name


class Tagging(models.Model):
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name='Model Name'
    )
    tagged_user = models.ManyToManyField(
        User, blank=True,
        related_name='tagged_user',
        verbose_name='Tagged Users'
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    def save(self, *args, **kwargs):
        return super(Tagging, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.object_id}-{self.content_type}'


def tag_users(data):
    try:
        content_type = ContentType.objects.get(model=data['model'])
        tag = Tagging.objects.create(
            content_type=content_type,
            object_id=data['object_id'],
        )
        for user_id in data['tags']:
            user = get_object_or_404(User, id=user_id)
            tag.tagged_user.add(user)
        return True
    except Exception as error:
        write_exception(message=error)
        return False


class Handover(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='handover_to')
    handover_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='handovers', blank=True, null=True)

    class Meta:
        ordering = ('-user__employee_name',)

    def __str__(self):
        return f"{self.user} --> {self.handover_to}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Handover, self).save(*args, **kwargs)
