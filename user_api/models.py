from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from employee.models import User
from api_key.models import APIKey
from utils_app.models import TimeStampedModel


class UserAPIKey(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='user_api_keys')

    class Meta:
        ordering = ('-user__employee_name',)
        verbose_name = "User API-Key"

    def __str__(self):
        return f"{self.user} --> {self.api_key}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(UserAPIKey, self).save(*args, **kwargs)


class TriggerEvent(models.Model):
    description = models.TextField(blank=True)
    name = models.CharField(max_length=100)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='trigger_events',
        help_text="Model that can trigger this event"
    )

    # Field-level configurations
    object_id_path = models.CharField(
        blank=True,
        max_length=255,
        help_text="Dot path to object ID in response data"
    )
    serializer_path = models.CharField(
        max_length=255,
        help_text="Python path to serializer"
    )
    model_filter_relation = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional relation path to final model"
    )

    class Meta:
        verbose_name = "Trigger Event"
        unique_together = ('name', 'content_type')  # Ensure unique name per content type

    def __str__(self):
        return f"{self.name} (Applies to: {self.content_type.model})"


class WebhookEndpoint(TimeStampedModel):
    target_url = models.URLField()
    name = models.CharField(max_length=255)
    headers = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    subscribed_events = models.ManyToManyField(TriggerEvent, related_name='webhook_endpoint')

    def __str__(self):
        return f"{self.name} ({', '.join(t.name for t in self.subscribed_events.all())})"

    class Meta:
        verbose_name = "Webhook Endpoint"
