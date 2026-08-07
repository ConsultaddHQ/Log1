import json
from unittest.mock import patch
from types import SimpleNamespace
from datetime import timedelta, date
from rest_framework.test import APITestCase, APIClient

from employee.models import Role, Team, User
from consultant.factories import Setup
from activity.views import create_activity
from project.models import ConsultantLeave
from consultant.models import Consultant, ConsultantProfile, ConsultantPOC, WorkAuth, ConsultantExit, ExitReason


class ConsultantV2VTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        for i in range(0, 5):
            self.setup.create_consultant()
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        res = self.client.get("/api/v2/consultant/?sort_by=name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count']['total'], 5)

    def test_filters(self):
        res = self.client.get("/api/v2/consultant/filters/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['on_bench'][0]['name'], 'non_pool')

    def test_export(self):
        res = self.client.get("/api/v2/consultant/export/")
        self.assertEqual(res.status_code, 200)


class ConsultantTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.user.is_superuser = True
        for role in ['marketer', 'recruiter']:
            self.setup.user.role.add(Role.objects.create(name=role))

        for i in range(0, 5):
            consultant_marketing = self.setup.create_consultant()
            self.setup.create_project(consultant_marketing, 'joined', 1)

        self.consultant = Consultant.objects.all()

        self.client = APIClient(self.setup.user)
        self.client.force_authenticate(user=self.setup.user)

    def test_consultant_list(self):
        res = self.client.get("/api/consultant/")
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
        res = self.client.get("/api/consultant/search/")
        self.assertEqual(res.status_code, 200)

        search_route = f"/api/consultant/search/?query={self.consultant.first().name}"
        search_res = self.client.get(search_route)
        self.assertEqual(search_res.data['data'].first()['name'], self.consultant.first().name)

    def test_create_and_update_education(self):
        payload = {
            "major": 'major',
            "edu_type": "phd",
            "city": "East Coast",
            "remark": "test remark",
            "end_date": "2021-12-15",
            "org_name": "organisation name test",
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
            "exp_type": "fresher",
            "remark": "test remark",
            "end_date": "2021-12-15",
            "company": "company name",
            "start_date": "2020-12-15",
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
        route = "/api/consultant/set_password/"
        payload = {"consultant_id": self.consultant.first().id, "new_password": "test"}
        res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['message'], 'Password Changed Successfully')

    def test_payroll_employer(self):
        payload = {'name': 'test_name'}
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
            "name": "test_employer",
            "feedback": "test_feedback",
            "rate": 60, "start": "2021-12-12",
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
            'country': 'USA',
            'current_city': 'West Coast',
            'date_of_birth': "1988-02-02",
            'recruiter': self.setup.user.id,
            'retention': self.setup.user.id,
            'payroll_employer': 'consultadd',
            'employer_start_date': "2020-01-01",
        }
        res = self.client.post("/api/consultant/", data=data)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.status_code, 201)

    def create_caps_team(self):
        return Team.objects.create(name='CAPS')

    @patch.dict('consultant.utils.__dict__', {
        'config': SimpleNamespace(
            TIMESHEET_APP_ADMIN='timesheet-admin@example.com',
            IPHONE_APP_LINK='https://apps.apple.com/timetrack',
            ANDROID_APP_LINK='https://play.google.com/timetrack',
            RELATIONS='relations@example.com',
        )
    })
    @patch('consultant.utils.send_email_', return_value=("sent", True, None))
    def test_create_caps_employee_creates_consultant_and_sends_timetrack_mail(self, send_email_mock):
        self.create_caps_team()
        role = Role.objects.create(name='engineer')
        payload = {
            "role": [role.id],
            "name": "CAPS User",
            "email": "caps_user@gmail.com",
            "phone": "1234567890",
            "gender": "male",
            "password": "consultadd123",
            "employee_id": 9001,
            "team": "CAPS",
        }
        res = self.client.post("/api/employee/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(employee_id=payload['employee_id'])
        consultant = Consultant.objects.get(email=user.email)
        self.assertEqual(consultant.internal_user_profile, user)
        self.assertTrue(consultant.internal_employee)
        self.assertTrue(consultant.is_active)
        self.assertTrue(consultant.has_usable_password())
        self.assertTrue(
            ConsultantLeave.objects.filter(
                consultant=consultant, leave_type__name='sick_leave', balance=48.0, granted=48.0
            ).exists()
        )
        self.assertEqual(send_email_mock.call_count, 1)
        mail_data = send_email_mock.call_args[0][0]
        self.assertEqual(mail_data['template'], '../templates/caps_timetrack_access.html')
        self.assertEqual(mail_data['to'], [consultant.email])
        self.assertTrue(mail_data['context']['new_user'])

    def test_update_consultant(self):
        route = f"/api/consultant/{self.consultant.first().id}/"
        res = self.client.put(route, data={"skills": 'Python', 'skype': "robert_jr"})
        self.assertEqual(res.data['message'], "Consultant Updated")
        self.assertEqual(res.data['data']['skills'], 'Python')
        self.assertEqual(res.status_code, 202)

    @patch.dict('consultant.utils.__dict__', {
        'config': SimpleNamespace(
            TIMESHEET_APP_ADMIN='timesheet-admin@example.com',
            IPHONE_APP_LINK='https://apps.apple.com/timetrack',
            ANDROID_APP_LINK='https://play.google.com/timetrack',
            RELATIONS='relations@example.com',
        )
    })
    @patch('consultant.utils.send_email_', return_value=("sent", True, None))
    def test_update_employee_to_caps_creates_consultant_and_sends_timetrack_mail(self, send_email_mock):
        user = User.objects.create(
            team=Team.objects.create(name='Engineering'),
            employee_id=9002,
            username=9002,
            email='caps_update@gmail.com',
            employee_name='CAPS Update User',
            gender='male',
        )
        caps_team = self.create_caps_team()
        route = "/api/employee/profile/"
        res = self.client.put(
            route,
            data=json.dumps({"user_id": user.id, "team_id": caps_team.id}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 202)
        consultant = Consultant.objects.get(email=user.email)
        self.assertEqual(consultant.internal_user_profile, user)
        self.assertTrue(consultant.is_active)
        self.assertTrue(consultant.has_usable_password())
        self.assertTrue(
            ConsultantLeave.objects.filter(
                consultant=consultant, leave_type__name='sick_leave', balance=48.0, granted=48.0
            ).exists()
        )
        self.assertEqual(send_email_mock.call_count, 1)

    def test_documents(self):
        route = f"/api/consultant/{self.consultant.first().id}/documents/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)

    def test_consultant_legal_login(self):
        route = "/api/consultant_petition/login/"
        data = {"email": f"{self.consultant.first().email}", "password": "123456789"}
        res = self.client.post(route, data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 202)

        data = {"email": "consultant@email.com", "password": "123456789"}
        res = self.client.post(route, data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 404)

        data = {"email1": "consultant@email.com", "password": "123456789"}
        res = self.client.post(route, data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 400)


class ConsultantMobileAuthTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    @staticmethod
    def create_login_consultant(email, team_name=None):
        internal_user = None
        if team_name:
            team = Team.objects.create(name=team_name)
            internal_user = User.objects.create(
                team=team,
                employee_id=9100 + Team.objects.count(),
                username=9100 + Team.objects.count(),
                email=f"user_{email}",
                employee_name='Mobile Internal User',
            )
        consultant = Consultant.objects.create(
            name='Mobile Consultant',
            email=email,
            is_active=True,
            first_login=False,
            internal_user_profile=internal_user,
            internal_employee=bool(internal_user),
        )
        consultant.set_password('consultadd123')
        consultant.save()
        return consultant

    def login(self, email):
        return self.client.post(
            "/api/consultant_auth/login/",
            data=json.dumps({
                "email": email,
                "password": "consultadd123",
                "uuid": "test-uuid",
                "fcm_token": f"fcm-{email}",
                "device_type": "android",
            }),
            content_type="application/json"
        )

    def test_mobile_login_response_includes_caps_true_for_caps_team(self):
        consultant = self.create_login_consultant('mobile_caps@example.com', team_name='CAPS')
        res = self.login(consultant.email)
        self.assertEqual(res.status_code, 202)
        self.assertIn('isCAPS', res.data['result'])
        self.assertTrue(res.data['result']['isCAPS'])

    def test_mobile_login_response_includes_caps_false_by_default(self):
        consultant = self.create_login_consultant('mobile_default@example.com')
        res = self.login(consultant.email)
        self.assertEqual(res.status_code, 202)
        self.assertIn('isCAPS', res.data['result'])
        self.assertFalse(res.data['result']['isCAPS'])

    def test_mobile_login_response_includes_caps_false_for_non_caps_team(self):
        consultant = self.create_login_consultant('mobile_non_caps@example.com', team_name='Engineering')
        res = self.login(consultant.email)
        self.assertEqual(res.status_code, 202)
        self.assertIn('isCAPS', res.data['result'])
        self.assertFalse(res.data['result']['isCAPS'])


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
            "linkedin": "linkedin_profile",
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
        self.con_exit = ConsultantExit.objects.all()
        self.client = APIClient()
        self.client.force_authenticate(self.setup.user)

    def test_list_consultant_con_exit(self):
        route = f"/api/consultant_exit/?query={self.marketing.consultant.name}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count']['total'], 1)

    def test_create_consultant_con_exit(self):
        ExitReason.objects.create(id=1, name="test exit reason")
        data = {
            "rehire": True,
            "reasons": ['1'],
            "notice_period": 1,
            "status": "complete",
            "type": "in_process",
            "last_date": "2020-09-09",
            "resign_date": "2020-09-08",
            "legal_status": "in_process",
            "exit_details": "text details",
            "cancel_reason": "test cancel reason",
            "consultant": self.marketing.consultant.id,
        }
        route = f"/api/consultant_exit/"
        res = self.client.post(route, data)
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(res.data['data'], {})

    def test_update_consultant_con_exit(self):
        data = {
            "exit_details": "test text here",
            "last_date": "2019-09-09"
        }
        route = f"/api/consultant_exit/{self.con_exit.first().id}/"
        res = self.client.put(route, data)
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['data']['exit_details'], 'test text here')

    def test_cancel_termination_(self):
        route = f"/api/consultant_exit/{self.con_exit.last().id}/cancel/"
        res = self.client.put(route, data={"cancel_reason": "test cancel exit"})
        self.assertEqual(res.data['message'], 'Exit process cancelled')
        self.assertEqual(res.status_code, 202)

        route = f"/api/consultant_exit/{self.con_exit.last().id}/cancel/"
        res = self.client.put(route)
        self.assertEqual(res.data['message'], 'Exit process can not be cancelled ')

    def test_termination_reason(self):
        ExitReason.objects.create(name="test exit reason")
        res = self.client.get(f"/api/consultant_exit/reason/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'].first()['name'], 'test exit reason')


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
