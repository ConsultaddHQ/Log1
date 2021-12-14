import json
import os.path

from rest_framework.test import APITestCase, APIClient

from attachment.models import create_attachment
from employee.models import Role
from consultant.models import Consultant, ConsultantMarketing
from activity.views import create_activity
from consultant.factories import Setup


class ConsultantFeedbackViewSetTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        consultant_marketing = self.setup.create_consultant()
        self.project = self.setup.create_project(consultant_marketing, 'new', 1)

        self.consultant = Consultant.objects.all()
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_get_consultant_feedback_list(self):
        route = f"/api/consultant/{self.consultant.first().id}/feedback/" \
                f"?query=admin&project={self.project.id}&feedback_type=[%22cfr%22]"
        res = self.client.get(route)
        self.assertEqual(res.data['data'][0]['project']['id'], self.project.id)
        self.assertEqual(res.data['data'][0]['feedback_type'], 'cfr')
        self.assertEqual(res.status_code, 200)

    def test_get_consultant_feedback_department(self):
        route = f"/api/consultant/{self.consultant.first().id}/feedback/department/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'], ['Engineering', 'Marketing', 'Legal', 'Recruitment', 'Relations', 'Finance'])

    def test_get_consultant_feedback_types(self):
        route = f"/api/consultant/{self.consultant.first().id}/feedback/feedback_types/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

    def test_get_consultant_project(self):
        route = f"/api/consultant/{self.consultant.first().id}/feedback/project/"
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
        create_route = f"/api/consultant/{self.consultant.first().id}/feedback/"
        res = self.client.post(create_route, data=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], 'Feedback added')

        payload['feedback_type'] = 'engineering_issue'
        res = self.client.post(create_route, data=payload)
        self.assertEqual(res.data['data']['department'], 'engineering')
        self.assertEqual(res.status_code, 201)

        route_update = f"/api/consultant/{self.consultant.first().id}/feedback/{res.data['data']['id']}/"
        payload['description'] = 'update consultant feedback'
        update_res = self.client.put(route_update, data=payload)
        self.assertEqual(update_res.status_code, 202)

    def test_request_feedback_mail(self):
        route = f"/api/consultant/{self.consultant.first().id}/feedback/request_feedback/"
        payload = {
            'department': ['Marketing', 'Engineering'],
            'feedback_type': 're_marketing'
        }
        res = self.client.post(route, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)


class ConsultantV2VTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        for i in range(0, 5):
            self.setup.create_consultant()
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
            consultant_marketing = self.setup.create_consultant()
            self.setup.create_project(consultant_marketing, 'new', 1)
        self.consultant = Consultant.objects.all()

        self.client = APIClient(self.setup.user)
        self.client.force_authenticate(user=self.setup.user)

    def test_consultant_list(self):
        route_list = f"/api/consultant/"
        res = self.client.get(route_list)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 5)

        route_list_with_query = f"/api/consultant/?query={self.consultant.first().name}"
        res_query = self.client.get(route_list_with_query)
        self.assertEqual(res_query.data['data'][0]['name'], self.consultant.first().name)
        self.assertEqual(res_query.status_code, 200)

    def test_retrieve_consultant(self):
        route = f"/api/consultant/{self.consultant.first().id}/"
        res = self.client.get(route)
        self.assertEqual(res.data['data']['name'], self.consultant.first().name)

        route_with_submission = f"/api/consultant/{self.consultant.first().id}/?submission={True}"
        res_submission = self.client.get(route_with_submission)
        self.assertEqual(res_submission.status_code, 200)

    def test_search_consultant(self):
        route = f"/api/consultant/search/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

        search_route = f"/api/consultant/search/?query={self.consultant.first().name}"
        search_res = self.client.get(search_route)
        self.assertEqual(search_res.data['data'].first()['name'], self.consultant.first().name)

    def test_create_and_update_education(self):
        payload = {
            "city": "East Coast",
            "major": 'major',
            "remark": "test remark",
            "org_name": "organisation name test",
            "edu_type": "phd",
            "end_date": "2021-12-15",
        }
        post_route = f"/api/consultant/{self.consultant.first().id}/education/"
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

        post_route = f"/api/consultant/{self.consultant.first().id}/experience/"
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
        get_route = f"/api/consultant/{self.consultant.first().id}/rate_revision/"
        get_res = self.client.get(get_route)
        self.assertEqual(len(get_res.data['data']), 1)
        self.assertEqual(get_res.status_code, 200)

        route = f"/api/consultant/{self.consultant.first().id}/rate_revision/"
        post_res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(post_res.status_code, 201)

        payload['end'] = None
        post_res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(post_res.status_code, 201)

    def test_documents(self):

        data = {
            "model": "consultant",
            "creator": self.setup.user,
            "object_id": self.consultant.first().id,
            "attachment_file": open(os.path.join(os.path.dirname(__file__), 'factories.py')),
            "attachment_type": "consultant",
        }
        create_attachment(data)
        route = f"/api/consultant/{self.consultant.first().id}/documents/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

    def test_margin(self):
        route = f"/api/consultant/{self.consultant.first().id}/margin/"
        res = self.client.get(route)
        self.assertEqual(res.data['data']['margin'], 10.0)
        self.assertEqual(res.status_code, 200)

    def test_create_consultant(self):
        data = {
            'ssn': 123564789866,
            'name': 'Robert Jr.',
            'email': 'rober@gmail.com',
            'is_w2': False,
            "skills": 'Java',
            'gender': 'Male',
            'phone_no': 99887766556,
            'current_city': 'West Coast',
            'date_of_birth': "1988-02-02",
            "visa_end": "2024-09-09",
            "visa_start": "2020-01-01",
            "visa_type": "h1b",
            'recruiter': self.setup.user.id,
            'retention': self.setup.user.id,
            'payroll_employer': 'consultadd',
            'employer_start_date': "2020-01-01",
        }
        route = f"/api/consultant/"
        res = self.client.post(route, data=data)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.status_code, 201)

    def test_update_consultant(self):
        data = {
            "skills": 'Python',
        }
        route = f"/api/consultant/{self.consultant.first().id}/"
        res = self.client.put(route, data=data)
        self.assertEqual(res.data['data']['skills'], 'Python')
        self.assertEqual(res.data['message'], "Consultant Updated")
        self.assertEqual(res.status_code, 202)


class ConsultantBenchTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        for i in range (0,5):
            consultant_marketing = self.setup.create_consultant()
            self.setup.create_project(consultant_marketing, 'new', 1)

        self.consultant = Consultant.objects.all()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_consultant_bench_list(self):
        route = f"/api/consultant_bench/?team=boto3&visa=[%22gc%22, %22h1b%22]&days=2 weeks"
        res = self.client.get(route)
        self.assertEqual(res.data['count']['total'], 5)
        self.assertEqual(res.status_code, 200)

        route = f"/api/consultant_bench/?query={self.consultant.first().email}&gender={self.consultant.first().gender}" \
                f"&skills=[%22{self.consultant.first().skills}%22]"
        res = self.client.get(route)
        self.assertEqual(res.data['data'].first()['skills'], self.consultant.first().skills)
        self.assertEqual(res.data['count']['in_offer'], 1)
        self.assertEqual(res.status_code, 200)


class ConsultantMarketingTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        for i in range(0, 5):
            consultant_marketing = self.setup.create_consultant()
            self.setup.create_project(consultant_marketing, 'new', 1)

        self.marketing = ConsultantMarketing.objects.all()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_list_consultant_marketing(self):
        route = f"/api/consultant_marketing/?consultant={self.marketing.first().consultant.id}"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 1)
        self.assertEqual(res.status_code, 200)

    def test_stop_consultant_marketing(self):
        data = {"end": "2020-09-09"}
        route = f"/api/consultant_marketing/{self.marketing.first().id}/stop_marketing/"
        res = self.client.put(route, data=data)
        self.assertEqual(res.data['message'], 'Marketing cycle stopped')
        self.assertEqual(res.status_code, 202)

    def test_create_consultant_marketing(self):
        data = {
            "consultant": self.marketing.first().consultant.id
        }
        route = f"/api/consultant_marketing/"
        res = self.client.post(route, data=data)
        self.assertEqual()