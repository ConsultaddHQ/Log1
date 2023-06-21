
from django.db import models
from employee.models import User
from consultant.models import Consultant

from django.utils import timezone
from utils_app.models import TimeStampedModel

class QuickActions(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    add_consultants = models.ManyToManyField(Consultant, related_name='quick_actions_add_consultant', blank=True)
    search_consultants = models.ManyToManyField(Consultant, related_name='quick_actions_search_consultant', blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"QuickActions  {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(QuickActions, self).save(*args, **kwargs)

class QuickActionAddConsultant(models.Model):
    quick_actions = models.ForeignKey(QuickActions, on_delete=models.CASCADE)
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class QuickActionSearchConsultant(models.Model):
    quick_actions = models.ForeignKey(QuickActions, on_delete=models.CASCADE)
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
