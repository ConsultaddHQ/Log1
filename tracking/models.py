from django.db import models
from employee.models import User
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

class Devices(models.Model):
    device_id = models.IntegerField(default=0)
    cookies_value = models.CharField(_('Cookies value'), max_length=20, null=False, unique=True, blank=False)
    created = models.DateTimeField(_('Created'), default=timezone.now, null=False, blank=False)
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='devices',
        verbose_name='users',
    )

    def save(self, *args, **kwargs):
        self.device_id = self.device_id + 1
        super().save(*args, **kwargs)  

    def __str__(self):
        return f"Device {self.id}"



class Location(models.Model):
    place_name = models.CharField(_('Place'), max_length=20, null=False, blank=False)
    state = models.CharField(_('State name'), max_length=20,  null=False, blank=False)
    country = models.CharField(_('Country'), max_length=20,  null=False, blank=False)
    pin_code = models.IntegerField(_('Pin code'), default=0, null=False, blank=False)
    created = models.DateTimeField(_('Created'), default=timezone.now)
    
    device = models.ForeignKey(
        Devices, on_delete=models.CASCADE,
        related_name='location',
        verbose_name='devices',
    )

    def __str__(self):
        return f"Device {self.id}"


class ExportData(models.Model):
    name = models.CharField(_('Data value type'), max_length=40, null=False, blank=False)    
    created = models.DateTimeField(_('Created'), default=timezone.now)
    device = models.ForeignKey(
        Devices, on_delete=models.CASCADE,
        related_name='export_data',
        verbose_name='devices',
    )

    def __str__(self):
        return f"Device {self.id}"