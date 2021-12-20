from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from attachment.models import Attachment
from employee.models import User, Tagging
from utils_app.models import TimeStampedModel
from project.models import Project, ProjectSupport


class ProjectDescription(TimeStampedModel):
    attachments = GenericRelation(Attachment)
    notes = models.TextField(_('Notes'), null=True)
    remark = models.TextField(_('Remark'), null=True)
    description = models.TextField(_('Description'), null=True)
    resource = models.TextField(_('Resource'), blank=True, null=True)
    technology = models.CharField(_('Technology'), max_length=500, null=True)
    update_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='description')
    consultant_preferred_time = models.CharField(_('Preferred Time'), max_length=30, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectDescription, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.project.id)


class ProjectUpdate(TimeStampedModel):
    UPDATE_TYPES = (
        ('project', 'Project'),
        ('training', 'Training'),
    )
    tagged_user = GenericRelation(Tagging)
    attachments = GenericRelation(Attachment)
    end = models.DateField(_("End"), null=True)
    start = models.DateField(_("Start"), null=True)
    update_by = models.ForeignKey(User, on_delete=models.CASCADE)
    update = models.TextField(_("̈Update"), null=True, blank=True)
    blocker = models.TextField(_("Blocker"), null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    type = models.CharField(_('Update Type'), choices=UPDATE_TYPES, max_length=20, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(ProjectUpdate, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.project.id)


class TrainingCheckList(TimeStampedModel):
    STATUS = (
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
        ('not_applicable', 'Not Applicable'),
    )
    position = models.IntegerField(_('Position'), null=True)
    task = models.TextField(_('Task'), blank=True, null=True)
    remark = models.TextField(_('Remark'), blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='check_list')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(TrainingCheckList, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.project.id)


class TrainingAgenda(TimeStampedModel):
    STATUS = (
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
        ('not_applicable', 'Not Applicable'),
    )
    position = models.IntegerField(_('Position'), null=True)
    remark = models.TextField(_('Remark'), blank=True, null=True)
    duration = models.CharField(_('Duration'), max_length=30, null=True)
    description = models.TextField(_('Description'), blank=True, null=True)
    assignment_given = models.BooleanField(_('Assignment Given'), null=True)
    status = models.CharField(_('Status'), max_length=30, null=True, blank=True)
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    assignment_submitted = models.BooleanField(_('Assignment Submitted'), null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='agenda')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agendas')

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(TrainingAgenda, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.project.id)
