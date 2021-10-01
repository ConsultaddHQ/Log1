from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from attachment.models import Attachment
from employee.models import User, Tagging
from utils_app.models import TimeStampedModel
from project.models import Project, ProjectSupport


class ProjectDescription(TimeStampedModel):
    description = models.TextField(_("Description"), null=True)
    technology = models.CharField(_('Technology'), max_length=500, null=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='description')

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectDescription, self).save(*args, **kwargs)

    def __str__(self):
        return self.project.id


class ProjectSupportUpdate(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    tagged_user = GenericRelation(Tagging)
    blocker = models.TextField(_("Description"), null=True)
    update_by = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectSupportUpdate, self).save(*args, **kwargs)

    def __str__(self):
        return self.project.id
