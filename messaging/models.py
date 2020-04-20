from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from employee.models import Asset


class Conversation(models.Model):
    user1 = models.ForeignKey(
        Asset, on_delete=models.CASCADE,
        verbose_name='User1',
        related_name='threads',
    )
    user2 = models.CharField(max_length=20)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)
    modified = models.DateTimeField(_('Modified'), default=timezone.now)

    def __str__(self):
        return f"{self.user1} - {self.user2}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        verbose_name='conversation',
        related_name='messages'
    )
    text = models.TextField(max_length=2000)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)
    is_sent = models.BooleanField(default=True)

    def __str__(self):
        return self.text
