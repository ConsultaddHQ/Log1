from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from utils_app.models import TimeStampedModel


class Field(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Field, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'
    

class DBTable(TimeStampedModel):
    name = models.CharField(_('Table Name'), max_length=100, null=True, blank=True)
    app_name = models.CharField(_('Table Type'), max_length=100, null=True, blank=True)
    own_property_count = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        
        return super(DBTable, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'


class Structure(TimeStampedModel):
    field_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    back_ref = models.CharField(_('Back Ref'), max_length=100, null=True, blank=True)
    front_ref = models.CharField(_('Front Ref'), max_length=100, null=True, blank=True)
    model_name = models.CharField(_('Model Name'), max_length=100, null=True, blank=True)
    field_type = models.ForeignKey(
        Field, on_delete=models.CASCADE,
        related_name='type',
        null=True, blank=True,
        verbose_name='Field Type'
    )
    db_table = models.ForeignKey(
        DBTable, on_delete=models.CASCADE,
        related_name='fields',
        null=True, blank=True,
        verbose_name='DB Table'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Structure, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.display_name}'
