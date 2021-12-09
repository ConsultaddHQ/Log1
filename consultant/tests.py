import json
import random
from datetime import date
from rest_framework.test import APITestCase, APIClient

from .factoryboy import ConsultantFactory, ConsultantMarketingFactory
from activity.views import create_activity
from employee.models import User, Team, Role
from project.models import Project, ProjectStatus, SupportStatus, ProjectSupport, ConsultantFeedback
from marketing.models import Submission, Lead, VendorCompany, VendorContact
from consultant.models import Consultant, ConsultantMarketing, PayrollEmployer


class Setup:
    def __init__(self):
        self.project_ids = []
        role = Role.objects.create(name="marketer")
        self.team = Team.objects.create(name="Consultadd")
        self.user = User.objects.create(
            team=self.team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        self.user.role.add(role)

    def create_project(self, marketing, status, count):
        vendor_company = VendorCompany.objects.create(name=f'vendor_company_name{count}')
        vendor_contact = VendorContact.objects.create(
            number='1234567890',
            company=vendor_company,
            name=f'vendor_name{count}',
            email=f'vendor.name{count}@email.com',
        )

        lead = Lead.objects.create(
            status='sub',
            owner=self.user,
            city='New York, US',
            primary_skill='Python',
            job_title='Python Developer',
            vendor_company=vendor_company,
            job_desc=f'Job Description{count}',
        )

        submission = Submission.objects.create(
            rate=50,
            lead=lead,
            is_complete=True,
            created_by=self.user,
            employer='Consultadd',
            client=f'client{count}',
            vendor_contact=vendor_contact,
            consultant_marketing=marketing,
        )
        project = Project.objects.create(
            is_msg_sent=True,
            city='New York, US',
            employer='Consultadd',
            submission=submission,
            start_date=date.today(),
            consultant=marketing.consultant,
        )

        ProjectStatus.objects.create(
            status=status,
            project=project,
            is_current=True,
        )
        if count % 5 != 0:
            project_support = ProjectSupport.objects.create(
                project=project,
                support=self.user,
                start=date.today(),
            )

            SupportStatus.objects.create(
                is_current=True,
                support=project_support,
                change_date=date.today(),
                frequency='more_than_2_days',
            )
            ConsultantFeedback.objects.create(
                project_id=project.id,
                description=f"test description {count}",
                created_by=self.user,
                consultant_id=marketing.consultant.id,
                department=random.choice(['Engineering', 'Legal', 'Marketing']),
                feedback_type="cfr",
                rating=random.choice([3, 4, 5]),
            )
            desc = f"Admin Demo added himself as support person"
            create_activity(project.id, 'projectsupport', self.user, desc, 'created')

        return project


class ConsultantFeedbackViewSetTest(APITestCase):

    def setUp(self):

        self.setup = Setup()
        self.consultant = ConsultantFactory()
        consultant_marketing = ConsultantMarketingFactory(consultant=self.consultant, in_pool=False, status='open')
        consultant_marketing.teams.add(self.setup.team)
        consultant_marketing.marketer.add(self.setup.user)
        self.project = self.setup.create_project(consultant_marketing, 'new', 1)
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_get_consultant_feedback_list(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/?query=admin&project={self.project.id}&feedback_type=[%22cfr%22]"
        res = self.client.get(route)
        self.assertEqual(res.data['data'][0]['project']['id'], self.project.id)
        self.assertEqual(res.data['data'][0]['feedback_type'], 'cfr')
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
            res.data['data'],
                (('cfr', 'CFR'), ('green_card', 'Green Card'), ('independent', 'Independent'),
                 ('pre_joining', 'Pre Joining'), ('2_week', '2 Week of Joining'),
                 ('re_marketing', 'Re-marketing'), ('rate_increment', 'Rate Increment'),
                 ('engineering_issue', 'Engineering Issue'))
        )

    def test_get_consultant_project(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/project/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'].first()['vendor'], 'vendor_company_name1')
        self.assertEqual(res.data['data'].first()['client'], 'client1')

    def test_create_and_update_consultant_feedback(self):
        payload = {
            "rating": 4,
            "department": "Marketing",
            "project": self.project.id,
            "feedback_type": "pre_joining",
            "description": "Consultant Feedback",
            "tagged_user": [self.setup.user.id]
        }
        create_route = f"/api/consultant/{self.consultant.id}/feedback/"
        res = self.client.post(create_route, data=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], 'Feedback added')

        payload['feedback_type'] = 'engineering_issue'
        res = self.client.post(create_route, data=payload)
        self.assertEqual(res.data['data']['department'], 'engineering')
        self.assertEqual(res.status_code, 201)

        route_update = f"/api/consultant/{self.consultant.id}/feedback/{res.data['data']['id']}/"
        payload['description'] = 'update consultant feedback'
        update_res = self.client.put(route_update, data=payload)
        self.assertEqual(update_res.status_code, 202)

    def test_request_feedback_mail(self):
        route = f"/api/consultant/{self.consultant.id}/feedback/request_feedback/"
        payload = {
            'department': ['Marketing', 'Engineering'],
            'feedback_type': 're_marketing'
        }
        res = self.client.post(route, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)


class ConsultantV2VTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        for i in range(0,5): ConsultantFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

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

        self.setup = Setup()
        self.setup.user.is_superuser = True
        for role in ['admin', 'marketer', 'recruiter']:
            self.setup.user.role.add(Role.objects.create(name=role))
        for i in range(0, 5):
            consultant = ConsultantFactory()
            if i % 2 == 0:
                consultant_marketing = ConsultantMarketingFactory(consultant=consultant, in_pool=False, status='open')
                consultant_marketing.teams.add(self.setup.team)
                consultant_marketing.marketer.add(self.setup.user)
                self.setup.create_project(consultant_marketing, 'new', 1)
        self.consultant = Consultant.objects.all()

        self.client = APIClient(self.setup.user)
        self.client.force_authenticate(user=self.setup.user)

    def test_consultant_list(self):
        route_list = f"/api/consultant/"
        res = self.client.get(route_list)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 3)

        route_list_with_query = f"/api/consultant/?query={self.consultant.first().name}"
        res_query = self.client.get(route_list_with_query)
        self.assertEqual(res_query.data['data'][0]['name'], self.consultant.first().name)
        self.assertEqual(res_query.status_code, 200)

    def test_retrieve_consultant(self):
        route = f"/api/consultant/{self.consultant.first().id}/"
        res = self.client.get(route)
        self.assertEqual(res.data['data']['name'], self.consultant.first().name)

        route_with_submission = f"/api/consultant/{self.consultant.first().id}/?submission={True}"
        res_submsission = self.client.get(route_with_submission)
        self.assertEqual(res_submsission.status_code, 200)

    def test_search_consultant(self):
        route = f"/api/consultant/search/"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 5)
        self.assertEqual(res.status_code, 200)

        search_route = f"/api/consultant/search/?query={self.consultant.first().name}"
        search_res = self.client.get(search_route)
        self.assertEqual(search_res.data['data'].first()['name'], self.consultant.first().name)

    def test_create_and_update_eductaion(self):
        payload = {
            "city": "East Coast",
            "major": 'major',
            "remark": "test remark",
            "org_name": "organisation name test",
            "edu_type": "phd",
            "end_date": "2021-12-15",
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

    def test_activities(self):
        create_activity(self.consultant.first().id, 'consultant', self.setup.user, "consultant added", 'create')
        route = f"/api/consultant/{self.consultant.first().id}/activities/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 1)

    def test_set_password(self):
        payload = {
            "consultant_id": self.consultant.first().id,
            "new_password": "test"
        }
        route = f"/api/consultant/set_password/"
        res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['message'], 'Password Changed Successfully')

    def test_marketing(self):
        route = f"/api/consultant/{self.consultant.first().id}/marketing/"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 1)
        self.assertEqual(res.status_code, 200)

        route_interview = f"/api/consultant/{self.consultant.first().id}/marketing/?stage=interview"
        res_interview = self.client.get(route_interview)
        self.assertEqual(len(res_interview.data['data']), 1)
        self.assertEqual(res.status_code, 200)

    def test_payroll_employer(self):
        payload = {
            'name': 'test_name',
        }

        create_route = f"/api/consultant/{self.consultant.first().id}/payroll_employer/"
        create_res = self.client.post(create_route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(create_res.status_code, 201)
        self.assertEqual(create_res.data['message'], "Employer added")

        payload['name'] = "name"
        update_route = f"/api/consultant/{create_res.data['data']['id']}/payroll_employer/"
        update_res = self.client.put(update_route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(update_res.status_code, 202)
        self.assertEqual(update_res.data['message'], "Employer updated")

        route = f"/api/consultant/{self.consultant.first().id}/payroll_employer/"
        get_res = self.client.get(route)
        self.assertEqual(get_res.status_code, 200)

    def test_rate_revision(self):
        payload = {
            "rate": 60,
            "name": "test_employer",
            "feedback": "test_feedback",
            "start": "2021-12-12",
            "consultant": self.consultant.first().id
        }
        route = f"/api/consultant/{self.consultant.first().id}/rate_revision/"
        post_res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(post_res.status_code, 201)

        payload['end'] = None
        post_res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(post_res.status_code, 201)

        get_route = f"/api/consultant/{self.consultant.first().id}/rate_revision/"
        get_res = self.client.get(get_route)
        self.assertEqual(len(get_res.data['data']), 2)
        self.assertEqual(get_res.status_code, 200)
