from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from employee.models import Asset
from utils_app.models import TimeStampedModel


class Conversation(TimeStampedModel):
    user1 = models.ForeignKey(
        Asset, on_delete=models.CASCADE,
        verbose_name='User1',
        related_name='threads',
    )
    user2 = models.CharField(_('User2'), max_length=20)

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Conversation, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.user1.number} - {self.user2}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        verbose_name='Conversation',
        related_name='messages'
    )
    text = models.TextField(_("Message text"), max_length=2000)
    read = models.BooleanField(_('Message Read or Unread'), default=False)
    is_sent = models.BooleanField(_('Message Sent or Received'), default=True)
    created = models.DateTimeField(_('Created'), default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        """
            On save timestamps
        """
        if not self.id:
            self.created = timezone.now()
        return super(Message, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.conversation.id} - {self.is_sent} - {self.created}"
