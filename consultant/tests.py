import json
from datetime import datetime, timedelta, date
from rest_framework.test import APITestCase, APIClient

from employee.models import Role
from consultant.factories import Setup
from consultant.models import Consultant, ConsultantMarketing, ConsultantProfile, ConsultantPOC, WorkAuth
from activity.views import create_activity


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
            'feedback_type': 're_marketing',
            'department': ['Marketing', 'Engineering'],
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

    def test_margin(self):
        route = f"/api/consultant/{self.consultant.first().id}/margin/"
        res = self.client.get(route)
        self.assertEqual(res.data['data']['margin'], 10.0)
        self.assertEqual(res.status_code, 200)

    def test_create_consultant(self):
        data = {
            'is_w2': False,
            'ssn': 123564789,
            "skills": 'Java',
            'gender': 'Male',
            "visa_type": "h1b",
            'name': 'Robert Jr.',
            'phone_no': 99887766556,
            "visa_end": "2024-09-09",
            'email': 'rober@gmail.com',
            "visa_start": "2020-01-01",
            'current_city': 'West Coast',
            'date_of_birth': "1988-02-02",
            'recruiter': self.setup.user.id,
            'retention': self.setup.user.id,
            'payroll_employer': 'consultadd',
            'employer_start_date': "2020-01-01",
        }
        res = self.client.post(f"/api/consultant/", data=data)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.status_code, 201)

    def test_update_consultant(self):
        route = f"/api/consultant/{self.consultant.first().id}/"
        res = self.client.put(route, data={"skills": 'Python'})
        self.assertEqual(res.data['data']['skills'], 'Python')
        self.assertEqual(res.data['message'], "Consultant Updated")
        self.assertEqual(res.status_code, 202)


class ConsultantBenchTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        for i in range(0, 5):
            consultant_marketing = self.setup.create_consultant()
            self.setup.create_project(consultant_marketing, 'new', 1)

        self.consultant = Consultant.objects.all()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_consultant_bench_list(self):
        consultant = self.consultant.first()
        route = f"/api/consultant_bench/?team=boto3&visa=[%22gc%22, %22h1b%22]&days=2 weeks"
        res = self.client.get(route)
        self.assertEqual(res.data['count']['total'], 5)
        self.assertEqual(res.status_code, 200)

        route = f"/api/consultant_bench/?query={consultant.email}&gender={consultant.gender}" \
                f"&skills=[%22{consultant.skills}%22]"
        res = self.client.get(route)
        self.assertEqual(res.data['data'].first()['skills'], self.consultant.first().skills)
        self.assertEqual(res.data['count']['in_offer'], 1)
        self.assertEqual(res.status_code, 200)


class ConsultantMarketingTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        self.marketing = self.setup.create_consultant()
        for i in range(0, 5):
            self.setup.create_project(self.marketing, 'new', 1)
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_list_consultant_marketing(self):
        route = f"/api/consultant_marketing/?consultant={self.marketing.consultant.id}"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 1)
        self.assertEqual(res.status_code, 200)

    def test_stop_consultant_marketing(self):
        data = {"end": "2020-09-09"}
        route = f"/api/consultant_marketing/{self.marketing.id}/stop_marketing/"
        res = self.client.put(route, data=data)
        self.assertEqual(res.data['message'], 'Marketing cycle stopped')
        self.assertEqual(res.status_code, 202)

    def test_create_consultant_marketing(self):
        data = {
            "consultant": self.marketing.consultant.id,
            "in_pool": False,
            "end": "2020-09-09",
            "start": "2018-09-09",
            "preferred_location": "WEST COAST",
            "teams": [self.setup.team.name],
            "marketers": [self.setup.user.id],
            "primary_marketer": self.setup.user.id,
        }
        self.marketing.status = 'close'
        self.marketing.save()
        route = f"/api/consultant_marketing/"
        res = self.client.post(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], 'Marketing started')

        data['reset_days'] = False
        self.marketing.consultant.status = 'terminated'
        self.marketing.consultant.save()
        route = f"/api/consultant_marketing/"
        res = self.client.post(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], 'Marketing started')

        self.marketing.start = date.today() + timedelta(days=3)
        self.marketing.save()
        route = f"/api/consultant_marketing/"
        res = self.client.post(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['message'], f'Marketing will start on {str(self.marketing.start)}')

        self.marketing.status = 'open'
        self.marketing.save()
        route = f"/api/consultant_marketing/"
        res = self.client.post(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['message'], f'Marketing is already started')

    def test_update_consultant_marketing(self):
        route = f"/api/consultant_marketing/{self.marketing.id}/"
        res = self.client.put(route, data={"preferred_location": "East Coast"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], f'Marketing cycle updated')
        self.assertEqual(res.data['data']['preferred_location'], 'East Coast')

    def test_remarketing(self):
        route = f"/api/consultant_marketing/remarketing/?consultant={self.marketing.consultant.id}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 1)

    def test_previous_marketing(self):
        route = f"/api/consultant_marketing/previous_marketing/?consultant={self.marketing.consultant.id}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 15)

        route = f"/api/consultant_marketing/previous_marketing/?consultant=78"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'], [])

    def test_marketer_assignment(self):
        data = {
            "marketers": [self.setup.user.id]
        }
        route = f"/api/consultant_marketing/{self.marketing.id}/marketer_assignment/"
        res = self.client.put(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], 'marketers assigned')

    def test_team_assignment(self):
        data = {
            "teams": [self.setup.team.id]
        }
        route = f"/api/consultant_marketing/{self.marketing.id}/team_assignment/"
        res = self.client.put(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], 'Team added')

    def test_remove_marketer(self):
        data = {
            "marketers": [self.setup.user.id]
        }
        route = f"/api/consultant_marketing/{self.marketing.id}/remove_marketer/"
        res = self.client.put(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Marketers removed")

    def test_remove_team(self):
        data = {
            "teams": [self.setup.team.id]
        }
        route = f"/api/consultant_marketing/{self.marketing.id}/remove_team/"
        res = self.client.put(route, data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Team removed")


class ConsultantProfileTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        self.marketing = self.setup.create_consultant()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_retrieve_consultant_profile(self):
        consultant_profile = ConsultantProfile.objects.all()
        route = f"/api/consultant_profile/{consultant_profile.first().id}/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['id'], consultant_profile.first().id)

    def test_list_consultant_profile(self):
        route = f"/api/consultant_profile/?con_id={self.marketing.consultant.id}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 1)

    def test_create_consultant_profile(self):
        data = {
            "title": "test",
            "education": "phd",
            "visa_type": 'h1b',
            "dob": "1980-09-09",
            "links": "this.link.",
            "visa_end": "2025-09-09",
            "visa_start": "2025-09-09",
            "current_city": "West Iowa",
            "linkedin": "likedin_profile",
            "consultant": self.marketing.consultant.id,
        }
        route = f"/api/consultant_profile/"
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], 'Profile created')
        self.assertNotEqual(res.data['data'], {})

    def test_update_consultant_profile(self):
        consultant_profile = ConsultantProfile.objects.all()
        route = f"/api/consultant_profile/{consultant_profile.first().id}/"
        res = self.client.put(route, data={"current_city": "West Iowa"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], 'Profile updated')
        self.assertEqual(res.data['data']['id'], consultant_profile.first().id)


class ConsultantPOCTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        self.marketing = self.setup.create_consultant()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_create_poc(self):
        data = {
            'poc_type': 'Recruiter',
            'consultant': self.marketing.consultant.id,
            'poc': self.setup.user.id,
        }
        route = f"/api/consultant_poc/"
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], "POC added")

    def test_update_poc(self):
        consultant_poc = ConsultantPOC.objects.all()
        route = f"/api/consultant_poc/{consultant_poc.first().id}/"
        res = self.client.put(route, data={"poc_type": "Retention"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['data']['poc_type'], "Retention")
        self.assertEqual(res.data['message'], "POC updated")


class WorkAuthTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        self.marketing = self.setup.create_consultant()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_create_consultant_work_auth(self):
        data = {
            'visa_end': '2028-09-09',
            'visa_start': '2020-09-09',
            'visa_type': 'h1b',
            'consultant': self.marketing.consultant.id
        }
        route = f"/api/consultant_work_auth/"
        res = self.client.post(route, data=data)
        self.assertNotEqual(res.data, {})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], "Work Auth added")

    def test_update_consultant_work_auth(self):
        work_auth = WorkAuth.objects.all()
        route = f"/api/consultant_work_auth/{work_auth.first().id}/"
        res = self.client.put(route, data={'visa_end': '2028-09-09'})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Work Auth added")
        self.assertEqual(res.data['data']['visa_end'], '2028-09-09')


class ConsultantExitTest(APITestCase):

    def setUp(self):
        self.setup = Setup()
        self.marketing = self.setup.create_consultant()
        self.marketing.consultant.status = 'terminated'
        self.marketing.consultant.save()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_list_consultant_work_auth(self):
        route = f"/api/consultant_exit/?query={self.marketing.consultant.name}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count']['total'], 1)
