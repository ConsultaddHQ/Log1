from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


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

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'cities'
