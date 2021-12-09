from datetime import date, timedelta
from rest_framework.test import APITestCase, APIClient

from activity.models import Activity
from activity.views import create_activity
from employee.models import User, Team, Role
from consultant.models import Consultant, ConsultantMarketing
from marketing.models import Submission, Lead, VendorCompany, VendorContact
from project.models import Project, ProjectStatus, ProjectSupport, SupportStatus, TimeSheet
from engineering.models import ProjectUpdate


class Setup:
    def __init__(self):
        self.project_ids = []
        self.consultant = None
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


class EngineeringViewSetTest(APITestCase):
    def setUp(self):
        self.setup = Setup()
        self.setup.projects_setup(11)

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list_engineering_projects(self):
        route = f"/api/engineering/?query=vendor_company_name2"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data'][0]['submission']['vendor'], 'vendor_company_name2')

        route = "/api/engineering/?page=1&page_size=10&filter_json={%22assignment%22:%22assigned%22}&filter_for=all"
        res = self.client.get(route)
        self.assertEqual(len(res.data['data']), 4)

        route = "/api/engineering/?filter_json={%22client%22:%22client2%22,%22assignment%22:%22assigned%22}"
        res = self.client.get(route)
        self.assertEqual(res.data['data'][0]['submission']['client'], 'client2')

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
        self.assertEqual(res.data['data'][0]['support_status'], 'Active')

    def test_retrieve_engineering_project(self):
        route = f"/api/engineering/{self.setup.project_ids[0]}/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['id'], self.setup.project_ids[0])

        route = f"/api/engineering/1/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 404)

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

        self.client = APIClient()
        self.client.force_authenticate(user=self.setup.user)

    def test_list(self):
        route = f"/api/project/{self.setup.project_ids[0]}/update/"
        res = self.client.get(route)
        self.assertEqual(res.status_code, 404)
