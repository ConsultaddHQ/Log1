from django.shortcuts import get_object_or_404
from django.core.management import BaseCommand
from django.contrib.contenttypes.models import ContentType

from consultant.models import Feedback
from employee.models import User, Tagging
from project.models import ConsultantFeedback


class Command(BaseCommand):
    def handle(self, *args, **options):
        feedbacks = Feedback.objects.all()
        content_type = ContentType.objects.get(model='consultantfeedback')
        for obj in feedbacks:
            department = obj.created_by.team.name.title()
            feedback = ConsultantFeedback.objects.create(
                rating=obj.rating,
                department=department,
                created_by=obj.created_by,
                consultant=obj.consultant,
                description=obj.feedback_text,
                feedback_type=obj.feedback_type,
            )
            tag_obj = obj.tagged_user
            if tag_obj:
                tag = Tagging.objects.create(
                    content_type=content_type,
                    object_id=feedback.id,
                )
                for tagged_user in obj.tagged_user.first().tagged_user.all():
                    user = get_object_or_404(User, id=tagged_user.id)
                    tag.tagged_user.add(user)
