from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractUser, PermissionsMixin

from api_key.models import APIKey
from utils_app.mailing import send_email
from employee.token import get_token_generator
from utils_app.models import TimeStampedModel


GENDER_CHOICE = (
    ('male', 'Male'),
    ('female', 'Female')
)

ASSET_TYPES = (
    ('email', 'Email'),
    ('social', 'Social'),
    ('number', 'Number'),
    ('job_board', 'Job Board')
)

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
            employee_id=int(employee_id),
            username=int(employee_id),
            email=email,
            team=team,
            employee_name=name,
            gender=gender,
        )

        user.phone = phone
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
            "admin@log1.com",
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
    email = models.EmailField(_('Email'))
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    role = models.ManyToManyField(Role, related_name='roles')
    employee_id = models.IntegerField(_('Employee ID'), unique=True)
    employee_name = models.CharField(_("Full Name"), max_length=100, blank=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    phone = models.CharField(_("Phone Number"), max_length=20, null=True, blank=True)
    avatar = models.ImageField(_("Profile Picture"), upload_to='avatar/', blank=True, null=True)
    gender = models.CharField(_('Gender'), choices=GENDER_CHOICE, max_length=10, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='employees', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = []

    class Meta:
        app_label = 'employee'

    def __str__(self):
        return f'{self.id}:{self.email}'

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

    @staticmethod
    def send_mail(mail_data):
        try:
            res = send_email(mail_data, "admin@log1.com")
            return res, "ok"
        except Exception as error:
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


def get_password_reset_token_expiry_time():
    return getattr(settings, 'RESET_TOKEN_EXPIRY_TIME', 24)


def clear_expired(expiry_time):
    ResetPasswordToken.objects.filter(created_at__lte=expiry_time).delete()


class Asset(TimeStampedModel):
    username = models.CharField(_('Username'), max_length=30)
    provider = models.CharField(_('Provider'), max_length=20)
    password = models.CharField(_('Password'), max_length=40)
    email = models.EmailField(_('Email'), null=True, blank=True)
    is_deleted = models.BooleanField(_('Is Deleted'), default=False)
    alter_email = models.EmailField(_('Alternate Email'), null=True, blank=True)
    number = models.CharField(_('Number'), max_length=40, null=True, blank=True)
    tech = models.CharField(_('Technology'), max_length=40, null=True, blank=True)
    remarks = models.CharField(_('Remarks'), max_length=300, null=True, blank=True)
    alter_number = models.CharField(_('Alternate Number'), max_length=20, null=True, blank=True)
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
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Asset, self).save(*args, **kwargs)

    def __str__(self):
        return self.owner.employee_name
