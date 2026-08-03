from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from employee.models import User
from marketing.models import Lead
from utils_app.models import TimeStampedModel


class JDParser(TimeStampedModel):
    jd = models.TextField(_("Job description"))
    job_title = models.CharField(max_length=50, null=True, blank=True)
    location = ArrayField(models.CharField(
        max_length=300), null=True, blank=True)
    lead = models.OneToOneField(
        Lead, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return self.job_title


# marketing mail classified data tables
class MarketingMail(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True)
    mail = models.CharField(
        _("Marketing Model"), max_length=100, blank=True, unique=True
    )

    def __str__(self):
        return self.mail


class MMailScrap(models.Model):
    FEEDBACK_CHOICES = (
        ('null', 'Null'),
        ('normal_mail', 'Normal mail'),
        ('job_requirement_mail', 'Job requirement mail'),
    )

    marketing_mail = models.ForeignKey(
        MarketingMail, on_delete=models.CASCADE, blank=True, null=True)
    sender_name = models.CharField(
        _("Sender Name"), max_length=100, blank=True, null=True)
    sender_mail = models.CharField(
        _("Sender Mail"), max_length=100, blank=True)
    # cc = models.CharField(_("CC"), blank=True, max_length=200,null=True)
    # bcc = models.CharField(_("BCC"), blank=True, max_length=200,null=True)
    subject = models.TextField(_("Subject"), blank=True)
    snippet = models.TextField(_("Snipper"), blank=True, null=True)
    body_text = models.TextField(_("Body Text"), blank=True, null=True)
    body_html = models.TextField(_("Body HTML"), blank=True, null=True)
    date = models.DateTimeField(_("Date"), blank=True, null=True,)
    keywords = models.TextField(_("Keywords"), blank=True, null=True)
    requirementMail = models.BooleanField(
        _("Requirement Mail"), blank=True, null=True, default=False)
    marketer_feedback = models.CharField(
        _('Marketer Feedback'), choices=FEEDBACK_CHOICES, max_length=20, null=True, blank=True, default="null")

    def __str__(self):
        return self.sender_name + " " + self.sender_mail
