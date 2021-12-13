import random
from faker import Faker
from datetime import date

from consultant.models import *
from activity.views import create_activity
from employee.models import Role
from marketing.models import Submission, VendorContact, VendorCompany, Lead, Interview
from project.models import ConsultantFeedback, SupportStatus, ProjectSupport, ProjectStatus, Project

fake = Faker()


class Setup:
    def __init__(self):
        self.project_ids = []
        role = Role.objects.create(name="marketer")
        self.team = Team.objects.create(name="boto3")
        self.user = User.objects.create(
            team=self.team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        self.user.role.add(role)

    def create_consultant(self):
        consultant = Consultant.objects.create(
            email=fake.email(),
            name=fake.name(),
            gender=random.choice(['male', 'female']),
            skills=random.choice(['Python', 'Java', 'React', 'JS', 'Ruby']),
            current_city=fake.city(),
            status='on_bench',
            work_type=random.choice(['c2c', 'full_time']),
            is_active=random.choice([True, False]),
            first_login=random.choice([True, False]),
            remote_only=random.choice([True, False]),
            phone_no=+19767546789,
            p_is_active=random.choice([True, False]),
            visa_petition=random.choice([True, False]),
        )

        consultant_marketing = ConsultantMarketing.objects.create(
            rtg=random.choice([True, False]),
            cycle=1,
            in_pool=random.choice([True, False]),
            previous_marketing_days=random.choice([0, 1, 2]),
            preferred_location=fake.city(),
            status='open',
            consultant=consultant,
        ),
        consultant_marketing[0].teams.add(self.team)
        consultant_marketing[0].marketer.add(self.user)
        ConsultantRateRevision.objects.create(
            rate=45.0,
            previous_rate=40.50,
            start=date.today(),
            feedback=fake.text(),
            consultant=consultant,
        )
        ConsultantPOC.objects.create(
            start=date.today(),
            poc_type='Retention',
            poc=self.user,
            consultant=consultant,
        )
        ConsultantPOC.objects.create(
            start=date.today(),
            poc_type='Recruiter',
            poc=self.user,
            consultant=consultant,
        )
        ConsultantProfile.objects.create(
            title='Original',
            visa_end="2020-09-07",
            visa_start="2017-09-07",
            education="phd",
            date_of_birth="1998-09-09",
            visa_type='h1b',
            current_city='West Iowa',
            profile_owner=self.user,
            consultant=consultant
        )
        WorkAuth.objects.create(
            is_current=True,
            visa_end="2022-12-12",
            visa_start="2018-11-11",
            visa_type=random.choice(['h1b', 'gc']),
            consultant=consultant,
        )
        return consultant_marketing[0]

    def create_project(self, marketing, status, count):

        vendor_company = VendorCompany.objects.create(
            name=f'vendor_company_name{count}'
        )
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
            rate=60,
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
            rate=55,
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
            Interview.objects.create(
                round= 0,
                feedback= fake.text(),
                guest_remark= fake.text(),
                coding_present= random.choice([True, False]),
                description= fake.text(),
                call_details= fake.text(),
                tech_stack= fake.text(),
                interview_mode=random.choice(['skype', 'webex', 'dial_in', 'hangouts', 'video_call', 'voice_call']),
                screening_type=random.choice(['ip_screening', 'vendor_screening', 'interview']),
                status= random.choice(['offer', 'scheduled', 'next_round']),
                supervisor=self.user,
                submission=submission,
            )

            desc = f"Admin Demo added himself as support person"
            create_activity(project.id, 'projectsupport', self.user, desc, 'created')

        return project
