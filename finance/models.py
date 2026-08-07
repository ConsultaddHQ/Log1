# from datetime import date
# from django.contrib.postgres.fields import ArrayField
# from django.db import models
# from django.utils import timezone
# from django.utils.translation import ugettext_lazy as _
# from django.contrib.contenttypes.fields import GenericRelation
#
# from marketing.models import Submission
# from consultant.models import Consultant
# from attachment.models import Attachment
# from employee.models import User, Tagging
# from project.models import Project
# from utils_app.models import TimeStampedModel, Choice
#
#
# class TimeSheet(TimeStampedModel):
#     TIMESHEET_STATUS = (
#         ('draft', 'Draft'),
#         ('updated', 'Updated'),
#         ('rejected', 'Rejected'),
#         ('approved', 'Approved'),
#         ('submitted', 'Submitted'),
#     )
#     attachments = GenericRelation(Attachment)
#     start = models.DateField(_('Start'), null=True, blank=True)
#     end = models.DateField(_('End'), null=True, blank=True)
#     hours = models.FloatField(max_length=20, null=True, blank=True)
#     project = models.ForeignKey(
#         Project, on_delete=models.PROTECT,
#         related_name='timesheets',
#         verbose_name='Project'
#     )
#     is_active = models.BooleanField(_('Is Active'), default=True)
#     remark = models.TextField(_("Remark"), null=True, blank=True)
#     submitted_at = models.DateTimeField(_('Submitted at'), null=True, blank=True)
#     con_comment = models.TextField(_("Consultant Comment"), null=True, blank=True)
#     status_updated_at = models.DateTimeField(_('Edited At'), null=True, blank=True)
#     additional_hours = models.FloatField(max_length=20, null=True, blank=True, default=0)
#     status = models.CharField(_("Status"), max_length=30, choices=TIMESHEET_STATUS, default='draft')
#     status_updated_by = models.ForeignKey(
#         User, on_delete=models.PROTECT,
#         related_name='timesheet_edits',
#         verbose_name='Edited BY',
#         null=True, blank=True
#     )
#
#     def save(self, *args, **kwargs):
#         if not self.id:
#             self.created = timezone.now()
#         self.modified = timezone.now()
#         return super(TimeSheet, self).save(*args, **kwargs)
#
#     def __str__(self):
#         return f'{self.id}:{self.project.consultant.name} - {self.status}'
#
#
# class ConsultantLeave(TimeStampedModel):
#     year = models.IntegerField(_('Year'))
#     balance = models.FloatField(_('Balance Left'))
#     granted = models.FloatField(_('Granted Leaves'))
#     is_expired = models.BooleanField(_('Leave Expired'), default=False)
#     leave_type = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='type')
#     consultant = models.ForeignKey(
#         Consultant, on_delete=models.PROTECT,
#         related_name='leaves_balance', verbose_name='Consultant'
#     )
#
#     def save(self, *args, **kwargs):
#         if not self.id:
#             self.created = timezone.now()
#         self.modified = timezone.now()
#         return super(ConsultantLeave, self).save(*args, **kwargs)
#
#     def __str__(self):
#         return f'{self.id}:{self.consultant.name}:{self.leave_type.name}'
#
# class Leave(TimeStampedModel):
#     LEAVE_STATUS = (
#         ('approved', 'Approved'),
#         ('rejected', 'Rejected'),
#         ('applied', 'Pending 2nd Level'),
#         ('pending', 'Pending 1st Level'),
#         ('rejected_1st_level', 'Rejected 1st Level')
#     )
#     attachment = GenericRelation(Attachment)
#     to_date = models.DateField(_("To Date"))
#     from_date = models.DateField(_("From Date"))
#     applied_on = models.DateField(_("Leave Apply Date"))
#     remarks = models.TextField(_('Remark'), null=True, blank=True)
#     description = models.TextField(_('Description'), null=True, blank=True)
#     status = models.CharField(_('Status'), max_length=30, choices=LEAVE_STATUS)
#     total_hours = models.FloatField(_('Total Hours'), max_length=30, null=True, blank=True)
#     leave_type = models.ForeignKey(
#         ConsultantLeave, on_delete=models.CASCADE,
#         related_name='leaves', verbose_name='Leave'
#     )
#     consultant = models.ForeignKey(
#         Consultant, null=True, blank=True,
#         on_delete=models.PROTECT, related_name='leaves', verbose_name='Consultant'
#     )
#
#     def save(self, *args, **kwargs):
#         if not self.id:
#             self.created = timezone.now()
#         self.modified = timezone.now()
#         return super(Leave, self).save(*args, **kwargs)
#
#     def __str__(self):
#         return f'{self.leave_type.consultant.name}'
#
#
# class TimesheetRequest(TimeStampedModel):
#     TIMESHEET_REQUEST_STATUS = (
#         ('reject', 'Reject'),
#         ('request', 'Request'),
#         ('accepted', 'Accepted'),
#     )
#     attachments = GenericRelation(Attachment)
#     end = models.DateField(_('End'), null=True, blank=True)
#     start = models.DateField(_('Start'), null=True, blank=True)
#     status = models.CharField(_("Status"), max_length=30, choices=TIMESHEET_REQUEST_STATUS)
#     reviewer_comment = models.TextField(_('Reviewer Comment'), null=True, blank=True)
#     consultant_comment = models.TextField(_('Consultant Comment'), null=True, blank=True)
#     reviewed_by = models.ForeignKey(
#         User, on_delete=models.PROTECT,
#         related_name='timesheet_req',
#         verbose_name='Reviewed BY',
#         null=True, blank=True
#     )
#     project = models.ForeignKey(
#         Project, on_delete=models.PROTECT,
#         related_name='timesheet_requests',
#         verbose_name='Project'
#     )
#
#     def save(self, *args, **kwargs):
#         if not self.id:
#             self.created = timezone.now()
#         self.modified = timezone.now()
#         return super(TimesheetRequest, self).save(*args, **kwargs)
#
#     def __str__(self):
#         return f'{self.id}:{self.project.consultant.name} - {self.status}'
#
#
# class TimetrackEvent(TimeStampedModel):
#     FEEDBACK_TYPE = (
#         ('external', 'External'),
#         ('internal ', 'Internal'),
#         ('feedback_not_required', 'Not Required')
#     )
#     end = models.DateField(_('End'), null=True, blank=True)
#     start = models.DateField(_('Start'), null=True, blank=True)
#     is_active = models.BooleanField(_('Is active'), default=True)
#     description = models.TextField(_('description'), null=True, blank=True)
#     action_link = models.TextField(_('action_link'), null=True, blank=True)
#     title = models.CharField(_('title'), max_length=80, null=True, blank=True)
#     feedback_type = models.CharField(_("Status"), max_length=30, choices=FEEDBACK_TYPE)
#     event_type = models.CharField(_('event_type'), max_length=30, null=True, blank=True)
#     image = models.ImageField(_("event Picture"), upload_to='timesheet_event/', blank=True, null=True)
#     consultants = models.ManyToManyField(Consultant, related_name='events', verbose_name='consultant')
#     created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='campaign', verbose_name='user')
#
#
# class TimetrackEventFeedback(models.Model):
#     feedback = models.TextField(_('feedback'), null=True, blank=True)
#     consultant = models.ForeignKey(
#         Consultant, on_delete=models.PROTECT,
#         related_name='event',
#         verbose_name='consultant'
#     )
#     event = models.ForeignKey(
#         TimetrackEvent, on_delete=models.CASCADE,
#         related_name='feedback',
#         verbose_name='event'
#     )