from rest_framework.test import APITestCase, APIClient

from employee.models import User
from project.models import Project
from .models import Consultant, ConsultantMarketing
from marketing.models import Submission, Lead, VendorCompany


class ConsultantFeedbackViewSetTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create(
            employee_id=1000,
            employee_name="Consultadd",
            password='consultadd',
            email='admin@log1.com',
        )

        self.consultant = Consultant.objects.create(
            email='test@log1.com',
            name='consultant name',
        )

        self.vendor_company = VendorCompany.objects.create(name='vendor_name')

        self.lead = Lead.objects.create(
            vendor_company=self.vendor_company
        )

        self.consultant_marketing = ConsultantMarketing.objects.create(
            primary_marketer=self.user,
            consultant=self.consultant
        )
        self.submission = Submission.objects.create(
            client='apple',
            lead=self.lead,
            created_by=self.user,
            consultant_marketing=self.consultant_marketing
        )

        self.project = Project.objects.create(
            submission=self.submission,
            consultant=self.consultant,

        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.payload = {
            "description": "feedback added",
            "project":self.project,
            "rating": 4,
            "department":None,
            "feedback_type":"pre_joining",
            "tagged_user":[],
        }

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
        self.assertEqual(res.data['data'], (('cfr', 'CFR'), ('issue', 'Issue'),
                         ('2_week', '2 Week'), ('pre_joining', 'Pre Joining'), ('independent', 'Independent'),
                         ('re_marketing', 'Re-marketing'), ('rate_increment', 'Rate Increment')))

    def test_get_consultant_project(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/project/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'].first()['vendor'], 'vendor_name')
        self.assertEqual(res.data['data'].first()['client'], 'apple')

    def test_create_consultant_feedback(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/"
        res = self.client.post(route, data=self.payload)
        self.assertEqual(res.status_code, 201)

    def test_request_feedback_mail(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/request_feedback/"
        payload = {
            'department': ['Marketing'],
            'feedback_type': 're_marketing'
        }
        res = self.client.post(route, data=payload)
        self.assertEqual(res.status_code, 201)
