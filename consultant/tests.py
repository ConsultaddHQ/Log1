import json
from datetime import date
from rest_framework.test import APITestCase, APIClient

from employee.models import User, Team, Role
from project.models import Project
from marketing.models import Submission, Lead, VendorCompany, VendorContact
from consultant.models import Consultant, ConsultantMarketing


class ConsultantFeedbackViewSetTest(APITestCase):

    def setUp(self):
        team = Team.objects.create(name="Consultadd")
        role = Role.objects.create(name="marketer")
        self.user = User.objects.create(
            team=team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        self.user.role.add(role)

        self.consultant = Consultant.objects.create(
            gender='male',
            skills='Python',
            status='on_bench',
            email='test@log1.com',
            name='consultant name',
            current_city='New York',
        )

        vendor_company = VendorCompany.objects.create(name='vendor_name')
        vendor_contact = VendorContact.objects.create(
            name='vendor_name',
            number='1234567890',
            company=vendor_company,
            email='vendor.name@email.com',
        )

        lead = Lead.objects.create(
            status='sub',
            owner=self.user,
            city='Remote, US',
            primary_skill='Python',
            job_desc='Job Description',
            job_title='Python Developer',
            vendor_company=vendor_company,
        )

        consultant_marketing = ConsultantMarketing.objects.create(
            status='open',
            start=date.today(),
            primary_marketer=self.user,
            consultant=self.consultant,
            preferred_location='East Coast',
        )
        consultant_marketing.teams.add(team)
        consultant_marketing.marketer.add(self.user)

        self.submission = Submission.objects.create(
            rate=50,
            lead=lead,
            client='apple',
            is_complete=True,
            employer='Consultadd',
            created_by=self.user,
            vendor_contact=vendor_contact,
            consultant_marketing=consultant_marketing
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_consultant_feedback_list(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/?query=&project=&feedback_type=[]"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

    def test_get_consultant_feedback_department(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/department/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'], ['Engineering', 'Marketing', 'Legal', 'Recruitment', 'Relations', 'Finance'])

    def test_get_consultant_feedback_types(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/feedback_types/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data['data'], (
                ('cfr', 'CFR'), ('issue', 'Issue'),
                ('2_week', '2 Week'), ('pre_joining', 'Pre Joining'), ('independent', 'Independent'),
                ('re_marketing', 'Re-marketing'), ('rate_increment', 'Rate Increment'))
        )

    def test_get_consultant_project(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/project/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'].first()['vendor'], 'vendor_name')
        self.assertEqual(res.data['data'].first()['client'], 'apple')

    def test_create_consultant_feedback(self):
        project = Project.objects.create(
            is_msg_sent=True,
            city='Remote, US',
            employer='Consultadd',
            start_date=date.today(),
            submission=self.submission,
            consultant=self.consultant,
        )
        payload = {
            "rating": 4,
            "tagged_user": [],
            "department": "Marketing",
            "project": project.id,
            "feedback_type": "pre_joining",
            "description": "Consultant Feedback",
        }
        route = f"/api/consultant/{self.consultant.id}/feedback/"
        res = self.client.post(route, data=payload)
        self.assertEqual(res.status_code, 201)

    def test_request_feedback_mail(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/request_feedback/"
        payload = {
            'department': ['Marketing'],
            'feedback_type': 're_marketing'
        }
        res = self.client.post(route, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
