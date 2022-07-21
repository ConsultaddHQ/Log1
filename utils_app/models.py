from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class TimeStampedModel(models.Model):
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)
    modified = models.DateTimeField(_('Modified'), default=timezone.now)

    class Meta:
        get_latest_by = 'modified'
        ordering = ('-modified', '-created',)
        abstract = True


class City(models.Model):
    name = models.CharField(_('City Name'), max_length=35)
    state = models.CharField(_('State'), max_length=20, blank=True, null=True)
    country = models.CharField(_('Country'), max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'cities'


class ScrumMeeting(TimeStampedModel):
    previous = models.BooleanField(_('Previous'), default=True)
    held_on = models.DateField(_('Held On'), default=timezone.now)

    def __str__(self):
        return f"{self.held_on} {self.previous}"

    class Meta:
        ordering = ('-held_on',)


class Choice(models.Model):
    name = models.CharField(_('Choice'), max_length=50)
    field = models.CharField(_('Model Field'), max_length=50)
    is_active = models.BooleanField(_('Is Active'), default=True)
    display_name = models.CharField(_('Display Choice'), max_length=50)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name='Model Name', null=True, blank=True
    )

    def save(self, *args, **kwargs):
        return super(Choice, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}-{self.field}-{self.content_type}'


class MapMail(TimeStampedModel):
    mail_id = models.CharField(_('Mail Id'), max_length=50)
    object_id = models.CharField(_('Object Id'), max_length=50)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name='Model Name', null=True, blank=True
    )
    
    def save(self, *args, **kwargs):
        return super(MapMail, self).save(*args, **kwargs)    
    
    def __str__(self):
        return self.content_type + ' ' + self.object_id 



class Field(models.Model):
    name = models.CharField(_('Field Name'), max_length=100)
    model = models.CharField(_('Model Name'), max_length=100)
    app_label = models.CharField(_('App Label'), max_length=100)

    def __str__(self):
        return f'{self.model}-{self.name}'


class ObjectGroup(models.Model):
    fields = models.ManyToManyField(Field, blank=True)
    name = models.CharField(_('Group Name'), max_length=100)
    model = models.CharField(_('Model Name'), max_length=100)
    status = models.CharField(_('Object Status'), max_length=100, blank=True)

    def __str__(self):
        return self.name


class CronJob(TimeStampedModel):
    name = models.CharField(_('Name'), max_length=100)
    enabled = models.BooleanField(_('Enabled'), default=True)
    description = models.TextField(_('Description'), blank=True, null=True)
    schedule = models.CharField(_('Schedule'), max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        return super(CronJob, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}-{self.modified}'


class CronError(models.Model):
    description = models.TextField(_('Description'), blank=True, null=True)
    job = models.ForeignKey(CronJob, on_delete=models.CASCADE, related_name='errors')
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        return super(CronError, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.job.name}-{self.created}'
