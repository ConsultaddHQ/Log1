import json
from datetime import date, datetime
from django.contrib.auth.models import ContentType
from rest_framework.test import APITestCase, APIClient

from activity.models import Activity
from employee.models import User, Team, Role
from project.models import Project
from utils_app.models import Choice, ObjectGroup, Field
from consultant.factories import Setup as consultant_setup
from marketing.models import Submission, Lead, VendorCompany, VendorContact, Test, Interview, Question, ChildQuestion


class Setup:
    def __init__(self):
        self.team = Team.objects.create(name="Boto3")
        role = Role.objects.create(name="marketer")
        self.user = User.objects.create(
            username=8000,
            team=self.team,
            employee_id=8000,
            employee_name='Demo',
            email='demo@log1.com',
            password='consultadd',
            technology=['python'],
        )
        self.user.role.add(role)

        self.vendor_company = VendorCompany.objects.create(
            name='vendor_company1',
            created_by='Consultadd Admin',
        )
        self.vendor_contact = VendorContact.objects.create(
            name="Vendor Name",
            number="6234456891",
            created_by=self.user,
            email="vendor@email.com",
            company_id=self.vendor_company.id,
        )

    def admin_setup(self):
        admin_role = Role.objects.create(name="admin")
        admin_user = User.objects.create(
            technology=[],
            username=8001,
            team=self.team,
            employee_id=8001,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        admin_user.role.add(admin_role)
        return admin_user

    @staticmethod
    def create_lead(data):
        content_type = ContentType.objects.get(model='lead')
        position = Choice.objects.create(name="SDE", display_name="Software Developer",
                                         content_type=content_type, field="position",)
        lead = Lead.objects.create(
            owner=data['user'], status=data.get("status", "Submitted"),
            city=data.get("city", "New York, US"), position=data.get("position", position),
            vendor_company=data.get("vendor_company"), job_desc=data.get("job_desc", "Job Description"),
            primary_skill=data.get("primary_skill", "Python"), job_title=data.get("job_title", "Python Developer"),
        )
        return lead

    def create_submission(self, data):
        consultant_marketing = consultant_setup.create_consultant(self)
        submission = Submission.objects.create(
            created_by=self.user,
            lead_id=data.get("lead"),
            rate=data.get("rate", 50),
            vendor_contact=self.vendor_contact,
            status=data.get("status", "Submitted"),
            client=data.get('client', 'client_name'),
            is_complete=data.get('is_complete', True),
            consultant_marketing=consultant_marketing,
            employer=data.get('employer', "Consultadd"),
        )
        Project.objects.create(city='New York, US', employer='Consultadd', submission=submission,start_date=date.today(),
                               consultant=consultant_marketing.consultant)
        return submission

    @staticmethod
    def create_test(data):
        return Test.objects.create(
            link=data.get("link", "test/link"), deadline=data.get("date", date.today()),
            status=data.get('status', "assigned"), submit_date=data.get("submit_date", datetime.now()),
            skills=data.get('skills', ["python"]), submission=data.get("submission"), submitted_by=data.get('user')
        )

    @staticmethod
    def create_interview(data):
        return Interview.objects.create(
                supervisor=data.get("user", None), submission=data.get("submission", None),
                round=data.get("round", 0), feedback=data.get("feedback", "feedback text"),
                interview_mode=data.get("interview_mode", "skype"), start_time=datetime.now(),
                tech_stack=data.get("tech_stack", "java, python"), coding_present=data.get("coding", True),
                status=data.get("status", "Scheduled"), screening_type=data.get('screening_type', 'interview'),
            )

    @staticmethod
    def create_question(data):
        return Question.objects.create(
            is_active=True,
            position=data.get('position', 1),
            category=data.get('category', 'basic'),
            answer_type=data.get('type', 'option'),
            title=data.get('title', 'Primary Technology'),
            form_name=data.get('form_name', 'test_online'),
            options=data.get('options', ['Java', 'Python']),
        )


class VendorCompanyTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        company_name = self.setup.vendor_company.name
        route = f"/api/vendor_company/?page=1&page_size=10&query={company_name}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['name'], company_name)

    def test_create(self):
        route = f"/api/vendor_company/"
        data = {'name': "VendorCompany2s"}
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 403)

        admin_user = self.setup.admin_setup()
        self.client.force_authenticate(user=admin_user)

        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 201)

        data = {'name': "VendorCompany2s"}
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 400)

        data = {'name': "VendorCompany2"}
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 400)


class VendorContactTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/vendor_contact/?company={self.setup.vendor_company.id}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['company__name'], self.setup.vendor_company.name)

    def test_retrieve(self):
        vendor_id = self.setup.vendor_contact.id
        route = f"/api/vendor_contact/{vendor_id}/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['id'], vendor_id)

    def test_create(self):
        route = "/api/vendor_contact/"
        data = {
            "number": "3123456789",
            "name": "Vendor Contact 2",
            "email": "vendor2@email.com",
        }
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 400)

        data = {
            "number": "3123456789",
            "name": "Vendor Contact 2",
            "email": "vendor2@email.com",
            "company": self.setup.vendor_company.id
        }
        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 201)

        res = self.client.post(route, data=data)
        self.assertEqual(res.status_code, 400)


class LeadTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.lead = self.setup.create_lead({"user": self.setup.user, "vendor_company": self.setup.vendor_company})

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        filter_json = {
            "status": ["Submitted"],
            "position": [self.lead.position.id],
            "vendor": [self.lead.vendor_company.id],
        }
        res = self.client.get(f"/api/lead/?query=python&filter_json={json.dumps(filter_json)}&sort_by=created")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"].first()["status"], "Submitted")

    def test_retrieve_and_delete(self):
        route = f"/api/lead/{self.lead.id}/"

        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["id"], self.lead.id)

        res = self.client.delete(route)
        self.assertEqual(res.status_code, 204)

    def test_create_and_update(self):
        data = {
            "job_desc": "Job description",
            "city": "West Coast",
            "job_title": "Job Title",
            "primary_skill": "python",
        }
        res = self.client.post(f"/api/lead/", data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["city"], "West Coast")

        self.setup.create_submission({"lead": res.data['data']['id']})
        res = self.client.put(f"/api/lead/{res.data['data']['id']}/", data={"city": "East Coast"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["data"]["city"], "East Coast")

    def test_fields(self):
        field = Field.objects.create(name="status", model="lead", app_label="marketing")
        group = ObjectGroup.objects.create(name="owner", model="lead", status="Submitted")
        group.fields.add(field)

        res = self.client.get(f"/api/lead/{self.lead.id}/fields/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0], "status")

    def test_archived(self):
        data = {"lead_ids": [self.lead.id]}
        self.lead.status = "new"
        self.lead.save()

        res = self.client.put(f"/api/lead/archived/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 202)
        lead = Lead.objects.get(id=self.lead.id)
        self.assertEqual(lead.status, 'archived')

        res = self.client.get(f"/api/lead/archived/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["status"], "archived")

    def test_map(self):
        res = self.client.get(f"/api/lead/map/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["city"], "New York, US")


class V2SubmissionTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        lead = self.setup.create_lead({"user": self.setup.user, "vendor_company": self.setup.vendor_company})
        self.submission = self.setup.create_submission({"lead": lead.id})

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_retrieve(self):
        res = self.client.get(f"/api/v2/submission/{self.submission.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["id"], self.submission.id)

    def test_tabs(self):
        res = self.client.get(f"/api/v2/submission/{self.submission.id}/tabs/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["test"], False)

    def test_fields(self):
        field = Field.objects.create(name="status", model="submission", app_label="marketing")
        group = ObjectGroup.objects.create(name="owner", model="submission", status="Submitted")
        group.fields.add(field)

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/fields/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0], "status")

    def test_documents(self):
        self.setup.create_test({"user": self.setup.user, "submission": self.submission})

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/documents/")
        self.assertEqual(res.status_code, 200)

    def test_profile(self):
        res = self.client.get(f"/api/v2/submission/{self.submission.id}/profile/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["name"], self.submission.consultant_marketing.consultant.name)

    def test_activity(self):
        content_type = ContentType.objects.get(model="submission")
        Activity.objects.create(
            object_id=self.submission.id, content_type=content_type,
            activity_type='created', user=self.setup.user, desc="activity description"
        )

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/activities/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["desc"], "activity description")

    def test_resume(self):
        self.setup.create_interview({"user": self.setup.user, "submission": self.submission})

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/resume/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "Submitted")

    def test_employer(self):
        Team.objects.create(name="Consultadd")

        res = self.client.get("/api/v2/submission/employer/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][1]["name"], "Consultadd")

    def test_interview(self):
        interview = self.setup.create_interview({"user": self.setup.user, "submission": self.submission})

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/interviews/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["id"], interview.id)

    def test_tests(self):
        test = self.setup.create_test({"user": self.setup.user, "submission": self.submission})

        res = self.client.get(f"/api/v2/submission/{self.submission.id}/tests/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["id"], test.id)

    def test_support(self):
        res = self.client.get(f"/api/v2/submission/{self.submission.id}/support/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["project"], self.submission.project.id)

    def test_project(self):
        res = self.client.get(f"/api/v2/submission/{self.submission.id}/project/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["id"], self.submission.project.id)


class SubmissionTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        lead = self.setup.create_lead({"user": self.setup.user, "vendor_company": self.setup.vendor_company})
        self.submission = self.setup.create_submission({"lead": lead.id})

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        filter_json = {
            "incomplete": False,
            "status": ["Submitted"],
            "client": ["client_name"],
            "marketer": [self.setup.user.id],
            "position": [self.submission.lead.position.id],
            "vendor": [self.submission.lead.vendor_company.id],
            "consultant": [self.submission.consultant_marketing.consultant.id]
        }

        res = self.client.get(f"/api/submission/?query=python&filter_json={json.dumps(filter_json)}&sort_by=created")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["id"], self.submission.id)

    def test_create(self):
        data = {
            "marketing_id": self.submission.consultant_marketing.id,
            "profile_id": self.submission.consultant_marketing.consultant.profiles.all().first().id,
            "rate": 60, "is_complete": False, "created_by": self.setup.user.id, "phone": "8765789723",
            "position": self.submission.lead.position.id, "email": "name@doamin.com", "city": "West Coast",
            "employer": 'Consultadd', "client": "client_name", "vendor_contact": self.setup.vendor_contact.id,
            "job_title": "Job Title", "vendor_company": self.setup.vendor_company.id, "job_desc": "Job description",
        }

        res = self.client.post("/api/submission/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["status"], "sub")

    def test_update(self):
        res = self.client.put(f"/api/submission/{self.submission.id}/", data={"rate": 40})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["data"]["rate"], 40)

    def test_feedback_check(self):
        self.setup.create_test({"user": self.setup.user, "submission": self.submission, "status": "feedback_due"})
        self.setup.create_interview({"user": self.setup.user, "submission": self.submission, "status": "feedback_due"})

        res = self.client.get(f"/api/submission/{self.submission.id}/feedback_check/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["test"], True)

    def test_suggestions(self):
        self.setup.create_test({"user": self.setup.user, "submission": self.submission, "status": "feedback_due"})
        self.setup.create_interview({"user": self.setup.user, "submission": self.submission, "status": "feedback_due"})
        consultant_id = self.submission.consultant_marketing.consultant.id

        res = self.client.get(f"/api/submission/suggestions/?client_name=client_name&consultant={consultant_id}"
                              f"&lead_id={self.submission.lead.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["client"], "client_name")

        res = self.client.get(f"/api/submission/suggestions/?client_name=client_name&consultant={consultant_id}"
                              f"&lead_id=0&company_id={self.setup.vendor_company.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["client"], "client_name")

    def test_did_you_mean(self):
        res = self.client.get("/api/submission/did_you_mean/?client=client_name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"], ["client_name"])

    def test_clients(self):
        res = self.client.get("/api/submission/client/?query=client_name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"], ["client_name"])


class VendorLayerTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        lead = self.setup.create_lead({"user": self.setup.user, "vendor_company": self.setup.vendor_company})
        self.submission = self.setup.create_submission({"lead": lead.id})

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_vendor_layer(self):
        data = {"company": self.setup.vendor_company.id, "submission": self.submission.id}

        res_create = self.client.post("/api/vendor_layer/", data=data)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(res_create.data['data']['level'], 1)

        res = self.client.get(f"/api/vendor_layer/{self.submission.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['id'], res_create.data['data']["id"])

        data = {"data": [{"id": res.data['data'][0]['id']}]}
        res = self.client.put(f"/api/vendor_layer/{res_create.data['data']['id']}/", data=json.dumps(data),
                              content_type="application/json")
        self.assertEqual(res.status_code, 202)

        res = self.client.delete(f"/api/vendor_layer/{res_create.data['data']['id']}/")
        self.assertEqual(res.status_code, 204)


class InterviewTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        lead = self.setup.create_lead({"user": self.setup.user, "vendor_company": self.setup.vendor_company})
        submission = self.setup.create_submission({"lead": lead.id})
        self.interview = self.setup.create_interview({"submission": submission, "user": self.setup.user})

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_retrieve(self):
        res = self.client.get(f"/api/interview/{self.interview.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["id"], self.interview.id)

    def test_list(self):
        filter_json = {
            "assignment": "assigned",
            "coding_interview": "yes",
            "status": "Scheduled",
            "ctb": [self.interview.supervisor.id],
            "client": ["client_name"],
            "marketer": [self.interview.supervisor.id],
            "vendor": [self.setup.vendor_company.id],
            "consultant": [self.interview.submission.consultant_marketing.consultant.id]
        }
        res = self.client.get(f"/api/interview/?query={self.interview.id}&filter_json={json.dumps(filter_json)}")
        self.assertEqual(res.status_code, 200)
        # self.assertEqual(res.data["data"][0]["id"], self.interview.id)


class TestViewSet(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.user = self.setup.user
        lead = self.setup.create_lead({"user": self.user, "vendor_company": self.setup.vendor_company})
        submission = self.setup.create_submission({"lead": lead.id})
        self.test = self.setup.create_test({"user": self.user, "submission": submission})

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_engineer_feedback(self):
        questions = self.setup.create_question({})
        data = [{"value": "java", "question_id": questions.id}]
        payload = {
            "feedback_form": json.dumps(data),
            "associates": [self.user.employee_id],
        }
        route = f"/api/test/{self.test.id}/engineer_feedback/"
        res = self.client.post(route, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["message"], "Feedback submitted")


class TestViewSet(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.user = self.setup.user
        self.setup.create_question({})

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        res = self.client.get("/api/question/?form_name=test_online")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]["position"], 1)

    def test_parent(self):
        payload = [
            {
                "position": 9,
                "child": None,
                "options": [],
                "category": "basic",
                "answer_type": "child",
                "title": "Number of coding questions",
             },
            {
                "child": None,
                "options": [],
                "position": 10,
                "category": "parent",
                "title": "Question 1",
                "answer_type": "headline",
             }
        ]
        for data in payload:
            self.setup.create_question(data)
        parent_question = Question.objects.get(title="Number of coding questions")
        child_question = ChildQuestion.objects.create(
            parent_question=Question.objects.get(title="Number of coding questions")
        )
        child_question.child_question.add(Question.objects.get(title="Question 1"))
        res = self.client.get(f"/api/question/{parent_question.id}/parent/?value=1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"][0]['title'], "Question 1")

    def test_create(self):
        role = Role.objects.create(name="superadmin")
        self.user.role.add(role)

        data = {
            "type": "option",
            "category": "basic",
            "title": "Secondary tech",
            "form_name": "test_online",
            "options": ["Django", "Flask", "Spring"]
        }
        res = self.client.post("/api/question/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["message"], "Question added to form")

        data = {
            "position": 2,
            "type": "option",
            "category": "basic",
            "title": "Platform",
            "form_name": "test_online",
            "options": ["Django", "Flask", "Spring"]
        }
        res = self.client.post("/api/question/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["message"], "Question added to form")
