from django.db import models
from utils_app.models import TimeStampedModel
from django.utils import timezone

from api_key.models import APIKey
from employee.models import User

# Create your models here.
class UserAPIKey(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='user_api_keys')

    class Meta:
        ordering = ('-user__employee_name',)

    def __str__(self):
        return f"{self.user} --> {self.api_key}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(UserAPIKey, self).save(*args, **kwargs)