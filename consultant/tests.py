import datetime
import json
from datetime import date
from rest_framework.test import APITestCase, APIClient

from .factoryboy import ConsultantFactory, ConsultantMarketingFactory
from employee.models import User, Team, Role
from project.models import Project, ProjectStatus
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

        self.project = Project.objects.create(
            is_msg_sent=True,
            city='Remote, US',
            employer='Consultadd',
            start_date=date.today(),
            submission=self.submission,
            consultant=self.consultant,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_consultant_feedback_list(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/?query=admin&project={self.project.id}&feedback_type=[%22cfr%22]"
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

    def test_create_and_update_consultant_feedback(self):
        payload = {
            "rating": 4,
            "department": "Marketing",
            "project": self.project.id,
            "feedback_type": "pre_joining",
            "description": "Consultant Feedback",
            "tagged_user": [self.user.id]
        }
        create_route = f"/api/consultant/{self.consultant.id}/feedback/"
        res = self.client.post(create_route, data=payload)
        route_update = f"/api/consultant/{self.consultant.id}/feedback/{res.data['data']['id']}/"
        payload['description'] = 'update consultant feedback'
        update_res = self.client.put(route_update, data=payload)
        self.assertEqual(update_res.status_code, 202)

    def test_request_feedback_mail(self):

        ProjectStatus.objects.create(project=self.project, status='new')
        route = f"/api/consultant/{self.consultant.id}/feedback/request_feedback/"
        payload = {
            'department': ['Marketing', 'Engineering'],
            'feedback_type': 're_marketing'
        }
        res = self.client.post(route, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)


class ConsultantV2VTest(APITestCase):

    def setUp(self):
        team = Team.objects.create(name="Consultadd")
        role = Role.objects.create(name="marketer")
        user = User.objects.create(
            team=team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        user.role.add(role)

        for i in range(0, 5):
            ConsultantFactory()
        self.client = APIClient(user)
        self.client.force_authenticate(user=user)

    def test_ConsultantV2_list(self):
        route = f"/api/v2/consultant/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count']['total'], 5)

    def test_ConsultantV2_list_filters(self):
        route = f"/api/v2/consultant/filters/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['on_bench'][0]['name'], 'non_pool')


class ConsultantTest(APITestCase):

    def setUp(self):
        team = Team.objects.create(name="Consultadd")
        user = User.objects.create(
            team=team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        for role in ['admin', 'marketer', 'recruiter']:
            user.role.add(Role.objects.create(name=role))

        for i in range(0, 5):
            consultant = ConsultantFactory()
            if i%2 == 0:
                consultant_marketing = ConsultantMarketingFactory(consultant=consultant, in_pool=False, status='open')
                consultant_marketing.teams.add(team)
                consultant_marketing.marketer.add(user)

        self.client = APIClient(user)
        self.client.force_authenticate(user=user)

    def test_consultant_list(self):
        route_list = f"/api/consultant/"
        res = self.client.get(route_list)
        self.assertEqual(res.status_code, 200)

        route_list_with_query = f"/api/consultant/?query={ConsultantFactory().name}"
        res_query = self.client.get(route_list_with_query)
        self.assertEqual(res_query.status_code, 200)

    def test_retrieve_consultant(self):
        route = f"/api/consultant/{ConsultantFactory(name='john').id}/"
        res = self.client.get(route)
        self.assertEqual(res.data['data']['name'], 'john')

        route_with_submission = f"/api/consultant/{ConsultantFactory(name='John').id}/?submission={True}"
        res_submsission = self.client.get(route_with_submission)
        self.assertEqual(res_submsission.status_code, 200)

    def test_search_consultant(self):
        route = f"/api/consultant/search/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

        search_route = f"/api/consultant/search/?query={res.data['data'].first()['name']}"
        search_res = self.client.get(search_route)
        self.assertEqual(search_res.data['data'].first()['name'], res.data['data'].first()['name'])

    def test_create_and_update_eductaion(self):
        payload = {
            "city":"East Coast",
            "major":'major',
            "remark":"test remark",
            "org_name":"organisation name test",
            "edu_type":"phd",
            "end_date":"2021-12-15",
        }
        post_route = f"/api/consultant/{ConsultantFactory().id}/education/"
        post_res = self.client.post(post_route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(post_res.status_code, 201)

        payload['city'] = 'West Coast'
        put_route = f"/api/consultant/{post_res.data['data']['id']}/education/"
        put_res = self.client.put(put_route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(put_res.status_code, 202)
        self.assertEqual(put_res.data['data']['city'], 'West Coast')

    def test_create_and_update_experience(self):
            payload = {
                "city": "East Coast",
                "title": 'Test title',
                "remark": "test remark",
                "company": "company name",
                "exp_type": "fresher",
                "end_date": "2021-12-15",
                "start_date": "2020-12-15"
            }

            post_route = f"/api/consultant/{ConsultantFactory().id}/experience/"
            post_res = self.client.post(post_route, data=json.dumps(payload), content_type="application/json")
            self.assertEqual(post_res.status_code, 201)
            payload['city'] = 'West Coast'

            put_route = f"/api/consultant/{post_res.data['data']['id']}/experience/"
            put_res = self.client.put(put_route, data=json.dumps(payload), content_type="application/json")
            self.assertEqual(put_res.status_code, 202)
            self.assertEqual(put_res.data['data']['city'], 'West Coast')
