from django.db import models
from employee.models import User
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from utils_app.models import TimeStampedModel


class Devices(TimeStampedModel):
    device_id = models.IntegerField(default=0)
    created = models.DateTimeField(_('Created'), default=timezone.now)
    cookies_value = models.CharField(_('Cookies value'), max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices', verbose_name='users')

    def save(self, *args, **kwargs):
        self.device_id = self.device_id + 1
        super().save(*args, **kwargs)  

    def __str__(self):
        return f"Device {self.id}"


class Location(TimeStampedModel):
    place_name = models.CharField(_('Place'), max_length=30, null=False, blank=False)
    country = models.CharField(_('Country'), max_length=30,  null=False, blank=False)
    pin_code = models.IntegerField(_('Pin code'), default=0, null=False, blank=False)
    state = models.CharField(_('State name'), max_length=30,  null=False, blank=False)
    display_name = models.CharField(_('Display name'), max_length=200, null=False, blank=False, default="")
    latitude = models.CharField(_("Latitude"),max_length=10, null=True, blank=False, default="")
    longitude = models.CharField(_("Longitude"),max_length=10, null=False, blank=False, default="")
    device = models.ForeignKey(Devices, on_delete=models.CASCADE, related_name='location', verbose_name='devices')

    def __str__(self):
        return f"Device {self.id}"


class ExportData(TimeStampedModel):
    created = models.DateTimeField(_('Created'), default=timezone.now)
    name = models.CharField(_('Data value type'), max_length=40, null=False, blank=False)
    device = models.ForeignKey(Devices, on_delete=models.CASCADE, related_name='export_data', verbose_name='devices')

    def __str__(self):
        return f"Device {self.id}"
