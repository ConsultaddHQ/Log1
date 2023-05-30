from django.db import models

from consultant.models import Consultant
from employee.models import User


class QuickActions(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    add_consultants = models.ManyToManyField(Consultant, related_name='quick_actions_add_consultant', blank=True)
    search_consultants = models.ManyToManyField(Consultant, related_name='quick_actions_search_consultant', blank=True)
