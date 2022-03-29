from unittest.mock import MagicMock
from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from rest_framework.test import APITestCase, APIClient

from activity.views import create_activity
from attachment.models import Attachment
from employee.models import User, Team, Role
from marketing.tests import Setup as MarketingSetup
from consultant.models import Consultant, ConsultantMarketing
from engineering.models import ProjectUpdate, ProjectDescription, TrainingAgenda, TrainingCheckList
from marketing.models import Submission, Lead, VendorCompany, VendorContact
from project.models import Project, ProjectStatus, ProjectSupport, SupportStatus, TimeSheet


class Setup:
    def __init__(self):
        self.project_ids = []
        self.consultant = None
        role = Role.objects.create(name="marketer")
        self.team = Team.objects.create(name="Consultadd")
        self.user = User.objects.create(
            username=1000,
            team=self.team,
            employee_id=1000,
            technology=['Python'],
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
            consultant=self.consultant,
        )

        ProjectStatus.objects.create(
            status=status,
            project=project,
            is_current=True,
        )

        TimeSheet.objects.create(
            hours=40,
            project=project,
            status='submitted',
            end=date.today() - timedelta(days=21),
            start=date.today() - timedelta(days=28),
            submitted_at=date.today() - timedelta(days=14),
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
            desc = f"Admin Demo added himself as support person"
            create_activity(project.id, 'projectsupport', self.user, desc, 'created')

        return project

    def projects_setup(self, count=1):
        self.consultant = Consultant.objects.create(
            gender='male',
            skills='Python',
            status='on_bench',
            email='test@log1.com',
            name='consultant name',
            current_city='New York',
        )
        consultant_marketing = ConsultantMarketing.objects.create(
            status='open',
            start=date.today(),
            primary_marketer=self.user,
            consultant=self.consultant,
            preferred_location='East Coast',
        )
        consultant_marketing.teams.add(self.team)
        consultant_marketing.marketer.add(self.user)

        for i in range(1, count):
            if i % 2 == 0:
                project = self.create_project(consultant_marketing, 'new', i)
            else:
                project = self.create_project(consultant_marketing, 'terminated', i)
            self.project_ids.append(project.id)

    def project_update(self, project_id):
        project = Project.objects.get(id=project_id)
        return ProjectUpdate.objects.create(
            project=project,
            start="2021-09-09",
            update_by=self.user,
            update="test update",
            blocker="test blocker",
            blocker_resolved=False,
        )

    def project_description(self, project_id):
        project = Project.objects.get(id=project_id)
        project_description = ProjectDescription.objects.create(
            notes="test notes",
            remark="test remark",
            description="test description",
            resource="test resource",
            technology="Java",
            update_by=self.user,
            project=project,
            consultant_preferred_time="11:00 am EST"
        )
        return project_description

    def training_agenda(self, project_id):
        project = Project.objects.get(id=project_id)
        training = TrainingAgenda.objects.create(
            position=2,
            project=project,
            status="complete",
            duration="2 weeks",
            remark="test remark",
            created_by=self.user,
            assignment_given=True,
            assignment_submitted=True,
            completion_date="2022-01-02",
            description="test description",
        )
        return training

    @staticmethod
    def training_check_list(project_id):
        project = Project.objects.get(id=project_id)
        checklist = TrainingCheckList.objects.create(
            position=2,
            project=project,
            status="complete",
            remark="test remark",
            task="training task test content"
        )
        return checklist


class EngineeringViewSetTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(11)

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list_engineering_projects(self):
        route = f"/api/engineering/?query=con"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], 'consultant name')

        route = "/api/engineering/?filter_json={%22project_status%22:%22new%22}"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 5)

        route = "/api/engineering/?filter_json={%22project_status%22:%22terminated%22}"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 5)

        route = "/api/engineering/?filter_json={%22start_date%22:{%22gte%22:%222021-12-07%22}}"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 5)

        route = "/api/engineering/?query=&page=1&page_size=10&filter_json={%22support%22:1}&filter_for=my"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 0)

        route = "/api/engineering/?query=&page=1&page_size=10&filter_json={%22support_status%22:%22active%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'][0]['support_status'], 'Training')

        route = "/api/engineering/?query=&page=1&page_size=10&filter_json={%22support_status%22:%22training%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'], [])

        route = "/api/engineering/?query=&page=1&page_size=10&filter_json={%22support_status%22:%22less_active%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'], [])

        route = "/api/engineering/?query=&page=1&page_size=10&filter_json={%22support_status%22:%22independent%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'], [])

        route = "/api/engineering/?filter_json={%22client%22:%22client2%22,%22assignment%22:%22assigned%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'][0]['submission']['client'], 'client2')

        route = "/api/engineering/?page=1&page_size=10&filter_json={%22assignment%22:%22assigned%22}&filter_for=all"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 4)

    def test_retrieve_engineering_project(self):
        route = f"/api/engineering/1/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 404)

        route = f"/api/engineering/{self.setup.project_ids[0]}/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['id'], self.setup.project_ids[0])

    def test_engineering_filters(self):
        route = f"/api/engineering/filters/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']['project_status']), 7)

    def test_engineering_activity(self):
        route = f"/api/engineering/{self.setup.project_ids[0]}/activity/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 1)

    def test_project_guidelines(self):
        route = f"/api/engineering/guidelines/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.data['data'].keys()), ['first_day', 'guideline'])

    def test_project_timesheet(self):
        start = date.today() - timedelta(days=28)
        route = f"/api/engineering/{self.setup.project_ids[0]}/timesheet/?start={start}"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['data']), 1)

        i = 1
        while True:
            if i in self.setup.project_ids:
                i += 1
            else:
                break
        route = f"/api/engineering/{i}/timesheet/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 404)


class ProjectUpdateViewSetTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(2)
        self.project_update = self.setup.project_update(self.setup.project_ids[0])
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/project/{self.setup.project_ids[0]}/updates/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(len(res.data['data']), [])

    def test_retrieve_update(self):
        route = f"/api/project/{self.setup.project_ids[0]}/updates/{self.project_update.id}/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['id'], self.project_update.id)

    def test_create(self):
        payload = {
            "blocker": "test_blocker",
            "update": "test_update",
            "type": 'project'
        }
        # mock_data = MagicMock(data=payload, FILES=['files'])
        route = f"/api/project/{self.setup.project_ids[0]}/updates/"
        res = self.client.post(route, data=payload)
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(len(res.data['message']), 'Project Update is added successfully')

    def test_update(self):
        payload = {
            "blocker": "test_blockers",
        }
        route = f"/api/project/{self.setup.project_ids[0]}/updates/{self.project_update.id}/"
        res = self.client.put(route, data=payload)
        self.assertEqual(res.status_code, 202)
        self.assertNotEqual(len(res.data['message']), 'Project update is edited successfully')

    def test_add_document(self):
        route = f"/api/project/{self.setup.project_ids[0]}/updates/{self.project_update.id}/add_document/"
        res = self.client.put(route, data={'file': 'file'})
        self.assertEqual(res.status_code, 202)
        self.assertNotEqual(len(res.data['message']), "Document is uploaded")

        attachment = Attachment.objects.all()
        route = f"/api/project/{self.setup.project_ids[0]}/updates/{self.project_update.id}/remove_document/"
        res = self.client.put(route, data={'attachment_id': attachment.first().id})
        self.assertEqual(res.status_code, 202)
        self.assertNotEqual(len(res.data['message']), "Document removed")

    def test_blocker(self):
        route = f"/api/project/{self.setup.project_ids[0]}/updates/{self.project_update.id}/blocker/"
        res = self.client.put(route, data={'blocker_resolved': True, "blocker_solution": "blocker solution content"})
        self.assertEqual(res.status_code, 202)
        update = get_object_or_404(ProjectUpdate, id=self.project_update.id)
        self.assertEqual(update.blocker_solution, "blocker solution content")


class ProjectSummaryViewSetTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(2)
        self.project_summary = self.setup.project_description(self.setup.project_ids[0])
        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/project/{self.setup.project_ids[0]}/summary/"
        res = self.client.get(route)
        self.assertNotEqual(res.data['data'], {})
        self.assertEqual(res.status_code, 200)

    def test_create(self):
        route = f"/api/project/{self.setup.project_ids[0]}/summary/"
        res = self.client.post(route, data={"notes":"test notes"})
        self.assertNotEqual(res.data['data'], {})
        self.assertEqual(res.status_code, 201)

        description = ProjectDescription.objects.get(id=res.data['data']['id'])
        description.delete()
        route = f"/api/project/{self.setup.project_ids[0]}/summary/"
        res = self.client.post(route)
        self.assertNotEqual(res.data['data'], {})
        self.assertEqual(res.status_code, 201)

        description = ProjectDescription.objects.get(id=res.data['data']['id'])
        description.delete()
        route = f"/api/project/{self.setup.project_ids[0]}/summary/"
        res = self.client.post(route, data={"remark": "test remark"})
        self.assertNotEqual(res.data['data'], {})
        self.assertEqual(res.status_code, 201)

    def test_update(self):
        route = f"/api/project/{self.setup.project_ids[0]}/summary/{self.project_summary.id}/"
        res = self.client.put(route, data={"notes":"test notes"})
        self.assertEqual(res.data['message'], "Project description updated")
        self.assertEqual(res.status_code, 202)

        route = f"/api/project/{self.setup.project_ids[0]}/summary/{self.project_summary.id}/"
        res = self.client.put(route, data={"remark" : "test remark"})
        self.assertEqual(res.data['message'], "Project description updated")
        self.assertEqual(res.status_code, 202)

        route = f"/api/project/{self.setup.project_ids[0]}/summary/{self.project_summary.id}/"
        res = self.client.put(route)
        self.assertEqual(res.data['message'], "Project description updated")
        self.assertEqual(res.status_code, 202)

    def test_technology(self):
        route = f"/api/project/{self.setup.project_ids[0]}/summary/technology/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Python', res.data['data'])

    def test_resource(self):
        route = f"/api/project/{self.setup.project_ids[0]}/summary/resource/"
        res = self.client.put(route, data={"resource": "resource content"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Project description updated")

        route = f"/api/project/{self.setup.project_ids[0]}/summary/resource/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['resource'], "resource content")


class TrainingAgendaTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(2)
        self.training = self.setup.training_agenda(self.setup.project_ids[0])

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/project/{self.setup.project_ids[0]}/training/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.data['data'], [])

    def test_create(self):
        data = {
            "duration": "2 weeks",
            "assignment_given": True,
            "remark": "test remark content",
            "description": "test description",
        }
        route = f"/api/project/{self.setup.project_ids[0]}/training/"
        res = self.client.post(route, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['message'], "Agenda added")

    def test_update(self):
        route = f"/api/project/{self.setup.project_ids[0]}/training/{self.training.id}/"
        res = self.client.put(route, data={"remark": "remark content",})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Agenda updated")

    def test_destroy(self):
        route = f"/api/project/{self.setup.project_ids[0]}/training/{self.training.id}/"
        res = self.client.delete(route)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data['message'], "Agenda Deleted")


class TrainingCheckListTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(2)
        self.checklist = self.setup.training_check_list(self.setup.project_ids[0])

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/project/{self.setup.project_ids[0]}/checklist/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.data['data'], [])

    def test_update(self):
        route = f"/api/project/{self.setup.project_ids[0]}/checklist/{self.checklist.id}/"
        res = self.client.put(route, data={"remark": "remark content",})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data['message'], "Checklist updated")


class EngineeringReportTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(3)

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        res = self.client.get("/api/engineer_report/?query=ad")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['employee_id'], 1000)

        res = self.client.get("/api/engineer_report/?query=client&category=client")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['employee_id'], 1000)

        res = self.client.get("/api/engineer_report/?query=ven&category=vendor_name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['employee_id'], 1000)

        res = self.client.get("/api/engineer_report/?query=ad&category=support_name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['employee_id'], 1000)

        res = self.client.get("/api/engineer_report/?query=consultant&category=consultant_name")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['employee_id'], 1000)

    def test_project_tab(self):
        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/project/?status=active&"
                              "category=consultant_name&query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/project/?category=client&query=cli")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/project/?query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

    def test_terminated_tab(self):
        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/terminated/?status=active&"
                              "category=consultant_name&query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

    def test_test_tab(self):
        user = self.setup.user
        project = Project.objects.filter(statuses__is_current=True, statuses__status='new')
        test = MarketingSetup.create_test({"user": user, "submission": project.first().submission})
        test.engineer.add(user)

        res = self.client.get(f"/api/engineer_report/{user.id}/test/?category=consultant_name&query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

        res = self.client.get(f"/api/engineer_report/{user.id}/test/?category=client&query=cli")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['client'], "client2")

        res = self.client.get(f"/api/engineer_report/{user.id}/test/?category=vendor_name&query=ven")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['vendor_company'], "vendor_company_name2")

        res = self.client.get(f"/api/engineer_report/{user.id}/test/?query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['vendor_company'], "vendor_company_name2")

    def test_interview_tab(self):
        user = self.setup.user
        project = Project.objects.filter(statuses__is_current=True, statuses__status='new')
        interview = MarketingSetup.create_interview({"user": user, "submission": project.first().submission})
        interview.guest.add(user)

        res = self.client.get(f"/api/engineer_report/{user.id}/interview/?category=consultant_name&query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['consultant']['name'], "consultant name")

        res = self.client.get(f"/api/engineer_report/{user.id}/interview/?category=client&query=cli&type=guest")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['client'], "client2")

        res = self.client.get(f"/api/engineer_report/{user.id}/interview/?category=vendor_name&query=ven&type=ctb")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['vendor_company'], "vendor_company_name2")

        res = self.client.get(f"/api/engineer_report/{user.id}/interview/?query=con")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['vendor_company'], "vendor_company_name2")

    def test_test_card(self):
        user = self.setup.user
        project = Project.objects.filter(statuses__is_current=True, statuses__status='new')
        test = MarketingSetup.create_test({"user": user, "submission": project.first().submission})
        test.engineer.add(user)

        res = self.client.get(f"/api/engineer_report/{user.id}/summary/test/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 1)

    def test_interview_card(self):
        user = self.setup.user
        project = Project.objects.filter(statuses__is_current=True, statuses__status='new')
        interview = MarketingSetup.create_interview({"user": user, "submission": project.first().submission})
        interview.guest.add(user)

        res = self.client.get(f"/api/engineer_report/{user.id}/summary/interview/?filter_by=this_quarter")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['guest_interview']['total'], 1)

    def test_project_card(self):
        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/summary/project/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 2)

    def test_technology_card(self):
        project = Project.objects.filter(statuses__is_current=True, statuses__status='new')
        ProjectUpdate.objects.create(project=project.first(), update_by=self.setup.user, type='project')
        ProjectDescription.objects.create(project=project.first(), technology='python')

        res = self.client.get(f"/api/engineer_report/{self.setup.user.id}/summary/technology/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 1)

    def test_category(self):
        data = [
            {'name': 'client', 'display_name': 'Client Name'},
            {'name': 'vendor_name', 'display_name': 'Vendor Name'},
            {'name': 'support_name', 'display_name': 'Support Name'},
            {'name': 'consultant_name', 'display_name': 'Consultant Name'},
        ]

        res = self.client.get(f"/api/engineer_report/category/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'], data)
