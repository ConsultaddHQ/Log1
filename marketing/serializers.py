from datetime import datetime
from rest_framework import serializers

from marketing.models import *
from consultant.models import Consultant
from django.db.models import Q
from project.utils import get_project_check_list
from project.models import Project, ProjectSupport
from activity.serializers import CommentGetSerializer
from consultant.serializers import ConsultantSerializer
from employee.serializers import UserSerializer, UserDetailSerializer
from attachment.serializers import AttachmentSerializer, AttachmentGetSerializer


class VendorCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCompany
        fields = '__all__'


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = ('id', 'name', 'email', 'number')


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    position_type = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()
    vendor_company_name = serializers.SerializerMethodField()

    @staticmethod
    def get_vendor_company_name(obj):
        return obj.vendor_company.name if obj.vendor_company else None

    @staticmethod
    def get_owner(obj):
        return obj.owner.employee_name

    @staticmethod
    def get_position_type(obj):
        return obj.get_position_type_display()

    @staticmethod
    def get_position_name(obj):
        if obj.position:
            return obj.position.display_name
        return None

    class Meta:
        model = Lead
        fields = ('id', 'job_desc', 'job_title', 'primary_skill', 'city', 'vendor_company_id', 'vendor_company_name',
                  'owner', 'status', 'created', 'modified', 'is_w2', 'position_name', 'position_type')


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'created', 'duration', 'start_date', 'end_date', 'city', 'feedback', 'consultant',
                  'vendor_address', 'client_address', 'payment_term', 'invoicing_period', 'is_msg_sent', 'check_list',
                  'reporting_details', 'rate', 'employer', 'attachments', 'is_remote', 'consultant_name')

    @staticmethod
    def get_consultant_name(obj):
        return obj.consultant.name

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)


class SubmissionSerializer(serializers.ModelSerializer):
    lead = LeadSerializer(read_only=True)
    test = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    interviews = serializers.SerializerMethodField()
    marketer_id = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    vendor_contact = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'date_of_birth', 'visa_type', 'visa_start', 'visa_end', 'education', 'linkedin', 'other_link',
                  'current_city', 'attachments', 'interviews', 'test', 'project', 'comments', 'marketer_name',
                  'marketer_id', 'consultant', 'is_complete')

    @staticmethod
    def get_attachments(obj):
        return []

    @staticmethod
    def get_vendor_contact(obj):
        return None

    @staticmethod
    def get_marketer_id(obj):
        return obj.created_by.id

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_project(obj):
        if hasattr(obj, 'project'):
            return ProjectSerializer(obj.project).data
        return None

    @staticmethod
    def get_consultant(obj):
        return ConsultantSerializer(obj.consultant).data

    @staticmethod
    def get_test(obj):
        return TestCreateSerializer(obj.test.all().order_by('created'), many=True).data

    @staticmethod
    def get_interviews(obj):
        return InterviewGetSerializer(obj.screening.all().order_by('round'), many=True).data

    @staticmethod
    def get_comments(obj):
        return CommentGetSerializer(obj.comments.filter(parent_comment=None), many=True).data


class VendorLayerSerializer(serializers.ModelSerializer):
    vendor_company = VendorCompanySerializer()

    class Meta:
        model = VendorLayer
        fields = '__all__'


class InterviewSerializer(serializers.ModelSerializer):
    submission = SubmissionCreateSerializer()
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)


class InterviewDetailSerializer(serializers.ModelSerializer):
    allow_status_change = serializers.SerializerMethodField()
    submission = SubmissionCreateSerializer()
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)

    @staticmethod
    def get_allow_status_change(obj):
        if obj.guest_type in ['coder', 'assistance', 'assigned'] and obj.coding_present is None:
            return False
        return True


class InterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        exclude = ('calendar_id',)


class InterviewGetSerializer(serializers.ModelSerializer):
    guest = UserSerializer(many=True)
    supervisor = UserSerializer()
    attachment_link = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)

    @staticmethod
    def get_attachment_link(obj):
        if obj.attachment_link:
            return obj.attachment_link.split('/')[-1]
        return None


class InterviewListSerializer(serializers.ModelSerializer):
    guest = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()
    supervisor_detail = serializers.SerializerMethodField()
    supervisor_feedback = serializers.SerializerMethodField()
    allow_status_change = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        exclude = ('notes', 'calendar_id', 'description', 'call_details', 'attachment_link', 'supervisor')

    @staticmethod
    def get_submission(obj):
        submission = obj.submission
        return {
            "id": submission.id,
            "client": submission.client,
            "marketer_id": obj.marketer.id,
            "work_type": submission.work_type,
            "job_title": submission.lead.job_title,
            "marketer_name": obj.marketer.employee_name,
            "vendor": submission.lead.vendor_company.name,
            "project": True if hasattr(submission, "project") else False,
            "position_name": submission.lead.position.display_name if submission.lead.position else None,
        }

    @staticmethod
    def get_consultant_name(obj):
        return obj.consultant.name

    @staticmethod
    def get_supervisor_detail(obj):
        if obj.supervisor.employee_id == 9999:
            data = {
                "call_given_by": "Consultant",
                "supervisor_name": obj.submission.consultant.name
            }
        else:
            data = {
                "call_given_by": "Interviewee",
                "supervisor_name": obj.supervisor.employee_name
            }
        return data

    @staticmethod
    def get_guest(obj):
        data = []
        for guest in obj.guest.all():
            data.append({'id': guest.id, 'name': guest.employee_name, 'email': guest.email})
        return data

    @staticmethod
    def get_allow_status_change(obj):
        if obj.guest_type in ['coder', 'assistance', 'assigned'] and obj.coding_present is None:
            return False
        return True

    @staticmethod
    def get_supervisor_feedback(obj):
        prv_date = datetime.strptime("2022-05-04", "%Y-%m-%d")
        if obj.start_time.replace(tzinfo=None) < prv_date:
            return True
        elif obj.supervisor_feedback.filter(question__form_name='interview') or obj.supervisor.employee_id == 9999:
            return True
        return False


class TestListSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    marketer_id = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    consultant_name = serializers.SerializerMethodField()
    engineer_associated = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'company_name', 'submission_id', 'marketer_name', 'marketer_id', 'client',
                  'consultant_name', 'submitted_by', 'job_title', 'skills', 'created', 'modified', 'assigned_to',
                  'engineer_associated', 'link', 'additional_details', 'platform')

    @staticmethod
    def get_client(obj):
        return obj.submission.client

    @staticmethod
    def get_marketer_id(obj):
        return obj.submission.created_by.id

    @staticmethod
    def get_job_title(obj):
        return obj.submission.lead.job_title

    @staticmethod
    def get_submitted_by(obj):
        if obj.submitted_by:
            return obj.submitted_by.employee_name
        return None

    @staticmethod
    def get_company_name(obj):
        return obj.submission.lead.vendor_company.name

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_consultant_name(obj):
        return obj.submission.consultant_marketing.consultant.name

    @staticmethod
    def get_engineer_associated(obj):
        return obj.engineer.all().values('id', 'employee_name')


class TestCreateSerializer(serializers.ModelSerializer):
    engineers = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'is_offline', 'feedback', 'link', 'additional_details', 'submit_date',
                  'engineer_remarks', 'is_video', 'skills', 'engineers', 'submitted_by', 'created', 'attachments',
                  'cancel_reason', 'assigned_to')

    @staticmethod
    def get_engineers(obj):
        if obj.engineer.all():
            return obj.engineer.all().values('id', 'employee_name')
        return None

    @staticmethod
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_submitted_by(obj):
        if obj.submitted_by:
            return {"id": obj.submitted_by.id, "employee_name": obj.submitted_by.employee_name}
        return None

    @staticmethod
    def get_attachments(obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data


class TestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'


class SubmissionV2Serializer(serializers.ModelSerializer):
    vendor_contact = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    vendor_layer = serializers.SerializerMethodField()
    work_type = serializers.SerializerMethodField()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'marketer_name', 'is_complete', 'vendor_layer', 'work_type')

    @staticmethod
    def get_vendor_layer(obj):
        return []

    @staticmethod
    def get_vendor_contact(obj):
        return None

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_work_type(obj):
        return obj.get_work_type_display()


class SubmissionV2DetailSerializer(serializers.ModelSerializer):
    vendor_layer = VendorLayerSerializer(read_only=True)
    marketer_name = serializers.SerializerMethodField()
    work_type = serializers.SerializerMethodField()
    vendor_contact = VendorContactSerializer()
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ('id', 'lead', 'rate', 'client', 'employer', 'email', 'phone', 'status', 'is_active', 'vendor_contact',
                  'marketer_name', 'is_complete', 'vendor_layer', 'work_type')

    @staticmethod
    def get_marketer_name(obj):
        return obj.created_by.employee_name

    @staticmethod
    def get_work_type(obj):
        return obj.get_work_type_display()


class SubmissionConProfile(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Consultant
        fields = ('id', 'name', 'email', 'current_city', 'phone_no', 'status', 'profile')

    def get_profile(self, obj):
        submission = self.context['submission']
        return {
            "linkedin": submission.linkedin,
            "visa_end": submission.visa_end,
            "education": submission.education,
            "visa_type": submission.visa_type,
            "other_link": submission.other_link,
            "visa_start": submission.visa_start,
            "current_city": submission.current_city,
            "date_of_birth": submission.date_of_birth,
            "marketer": submission.created_by.employee_name,
        }


class InterviewV2Serializer(serializers.ModelSerializer):
    supervisor = serializers.SerializerMethodField()
    guest = UserDetailSerializer(many=True)
    permission = serializers.SerializerMethodField()
    marketer_name = serializers.SerializerMethodField()
    guest_feedback = serializers.SerializerMethodField()
    attachment_link = serializers.SerializerMethodField()
    allow_status_change = serializers.SerializerMethodField()
    supervisor_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        exclude = ('calendar_id',)

    def get_permission(self, obj):
        user = self.context.get('user')
        if user in [obj.marketer, obj.supervisor]:
            return {'update': True}
        authentic_user_id = []
        authentic_user_id.extend(user.handovers.all().values_list('user__id', flat=True))
        if obj.marketer.id in authentic_user_id or obj.supervisor.id in authentic_user_id:
            return {"update": True}
        return {"update": False}

    @staticmethod
    def get_attachment_link(obj):
        if obj.attachment_link:
            return obj.attachment_link.split('/')[-1]
        return None

    @staticmethod
    def get_marketer_name(obj):
        return obj.submission.created_by.employee_name

    @staticmethod
    def get_allow_status_change(obj):
        if obj.guest_type in ['coder', 'assistance', 'assigned'] and obj.coding_present is None:
            return False
        return True

    @staticmethod
    def get_supervisor_feedback(obj):
        if obj.supervisor_feedback.filter(question__form_name='interview'):
            answers = Answer.objects.filter(object_id=obj.id, question__form_name='interview').exclude(
                question__category='child').order_by("question__position")
            return QuestionAnswerSerializer(answers, many=True).data
        return None

    @staticmethod
    def get_guest_feedback(obj):
        if obj.supervisor_feedback.filter(question__form_name='coding'):
            answers = Answer.objects.filter(object_id=obj.id, question__form_name='coding').exclude(
                question__category='child').order_by("question__position")
            return QuestionAnswerSerializer(answers, many=True).data
        return None

    @staticmethod
    def get_supervisor(obj):
        if obj.supervisor.employee_id == 9999:
            data = {
                "call_given_by": "Consultant",
                "supervisor_name": obj.submission.consultant.name
            }
        else:
            data = {
                "call_given_by": "Interviewee",
                "supervisor_name": obj.supervisor.employee_name
            }
        return data


class QuestionAnswerSerializer(serializers.ModelSerializer):
    question_answer = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = ('question_answer',)

    @staticmethod
    def get_question_answer(obj):
        if obj.answer and ": " in obj.answer and obj.question.answer_type in ["yes_attachment", "no_attachment",
                                                                              "yes_remark", "no_remark"]:
            answer = obj.answer.split(": ")
        else:
            answer = [obj.answer, None]
        data = {
            "child": [],
            "answer": answer[0],
            "remark": answer[1],
            "answer_id": obj.id,
            "ques_id": obj.question.id,
            "ques_title": obj.question.title,
            "ques_category": obj.question.category,
            "answer_type": obj.question.answer_type,
            "attachment": AttachmentGetSerializer(
                obj.attachment.filter(attachment_type='test_feedback', content_type__model='answer'), many=True
            ).data,
        }
        if obj.question.category == 'parent_child':
            for question in obj.question.child_question.first().child_question.filter().order_by('position'):
                child_ques_answers = Answer.objects.filter(
                    object_id=obj.object_id, parent_question=question
                ).order_by('question__position')
                if child_ques_answers:
                    child_data = {
                        "ques_id": question.id, "ques_title": question.title, "child": [],
                        "ques_category": question.category, "answer_type": question.answer_type,
                    }
                    for question_answer in child_ques_answers:
                        child_data['child'].append(QuestionAnswerSerializer(question_answer).data)
                    data["child"].append(child_data)
        return data


class TestGetSerializer(serializers.ModelSerializer):
    engineers = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    attachments = AttachmentGetSerializer(many=True)
    assigned_to = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()
    engineer_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'status', 'deadline', 'is_offline', 'feedback', 'link', 'additional_details', 'submit_date',
                  'engineer_remarks', 'is_video', 'skills', 'engineers', 'submitted_by', 'created', 'attachments',
                  'cancel_reason', 'assigned_to', 'permission', 'engineer_feedback', 'platform')

    @staticmethod
    def get_engineers(obj):
        if obj.engineer.all():
            return obj.engineer.all().values('id', 'employee_name')
        return None

    @staticmethod
    def get_assigned_to(obj):
        return obj.assign_to.all().values('id', 'employee_name')

    @staticmethod
    def get_submitted_by(obj):
        if obj.submitted_by:
            return {
                "id": obj.submitted_by.id,
                "employee_name": obj.submitted_by.employee_name,
            }
        return None

    def get_permission(self, obj):
        user = self.context.get('user')
        if user == obj.marketer:
            return {'update': True}
        authentic_user_id = []
        authentic_user_id.extend(user.handovers.all().values_list('user__id', flat=True))
        if obj.marketer.id in authentic_user_id:
            return {"update": True}
        return {"update": False}

    @staticmethod
    def get_engineer_feedback(obj):
        answers = Answer.objects.filter(object_id=obj.id).exclude(question__category='child').order_by("question__position")
        return QuestionAnswerSerializer(answers, many=True).data


class SubmissionSupportSerializer(serializers.ModelSerializer):
    support = UserDetailSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSupport
        fields = '__all__'

    @staticmethod
    def get_status(obj):
        statuses = obj.statuses.filter(is_current=True)
        if statuses:
            support_status = statuses.first()
            return {"id": support_status.id, "frequency": support_status.frequency}
        return None


class ProjectV2Serializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    check_list = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    remote_consultant = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'status', 'feedback', 'check_list', 'attachments', 'created', 'city', 'remote_consultant',
                  'duration', 'invoicing_period', 'feedback', 'client_address', 'vendor_address', 'payment_term',
                  'start_date', 'end_date', 'rate', 'employer', 'reporting_details', 'is_remote', 'permission')

    @staticmethod
    def get_remote_consultant(obj):
        return {
            "id": obj.consultant.id,
            "name": obj.consultant.name
        }

    @staticmethod
    def get_status(obj):
        status = obj.statuses.filter(is_current=True)
        if status:
            return status.first().status
        return None

    def get_permission(self, obj):
        user = self.context.get('user')
        if user == obj.submission.created_by or 'finance' in user.roles:
            return {'update': True}
        authentic_user_id = []
        authentic_user_id.extend(user.handovers.all().values_list('user__id', flat=True))
        if obj.submission.created_by.id in authentic_user_id:
            return {"update": True}
        return {"update": False}

    @staticmethod
    def get_attachments(obj):
        return AttachmentGetSerializer(obj.attachments.all(), many=True).data

    @staticmethod
    def get_check_list(obj):
        return get_project_check_list(obj)


class QuestionSerializer(serializers.ModelSerializer):
    dependent = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ("id", "title", "category", "answer_type", "position", "is_required", "options", "dependent",
                  "update_options")

    @staticmethod
    def get_dependent(obj):
        if obj.child_question.first() and obj.answer_type in ['yes_question', 'no_question']:
            return QuestionSerializer(obj.child_question.first().child_question.all(), many=True).data
        return None


class ParentQuestionSerializer(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()
    dependent = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ("id", "title", "category", "answer_type", "position", "is_required", "options", "child", "dependent")

    @staticmethod
    def get_child(obj):
        if obj.child_question.first():
            return QuestionSerializer(
                obj.child_question.first().child_question.filter().order_by('position'), many=True
            ).data
        return None

    @staticmethod
    def get_dependent(obj):
        if obj.child_question.first() and obj.answer_type in ['yes_question', 'no_question']:
            return QuestionSerializer(obj.child_question.first().child_question.all(), many=True).data
        return None


class TeamStructureSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    is_scrum = serializers.SerializerMethodField()
    current_offers = serializers.SerializerMethodField()
    assign_consultant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'employee_name', 'shift', 'technology', 'current_offers', 'assign_consultant',
                  'team', 'is_scrum')

    @staticmethod
    def get_team(obj):
        if obj.team:
            return {
                "id": obj.team.id, "name": obj.team.name
            }
        return None

    @staticmethod
    def get_is_scrum(obj):
        if obj.role.filter(name='admin'):
            return True
        return False

    @staticmethod
    def get_current_offers(obj):
        offers = obj.submissions.filter(status__in=['project'])
        if offers:
            data = {
                "count": len(offers),
                "project": [{
                    "id": offer.id, "client": offer.client
                } for offer in offers]
            }
            return data
        return []

    @staticmethod
    def get_assign_consultant(obj):
        consultants = obj.marketed.filter(status='open')
        if consultants:
            data = {
                "count": len(consultants),
                "consultant": [{
                    "id": consultant.consultant.id, "consultant_name": consultant.consultant.name
                } for consultant in consultants]
            }
            return data
        return []
