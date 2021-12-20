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
        self.team = Team.objects.create(name="boto3")
        self.user = User.objects.create(
            team=self.team,
            employee_id=1000,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        self.user.role.add(Role.objects.create(name="marketer"))
        self.user.role.add(Role.objects.create(name="superadmin"))

    def create_consultant(self):
        consultant = Consultant.objects.create(
            name=fake.name(),
            status='on_bench',
            email=fake.email(),
            phone_no=+19767546789,
            current_city=fake.city(),
            is_active=random.choice([True, False]),
            first_login=random.choice([True, False]),
            remote_only=random.choice([True, False]),
            p_is_active=random.choice([True, False]),
            gender=random.choice(['male', 'female']),
            visa_petition=random.choice([True, False]),
            work_type=random.choice(['c2c', 'full_time']),
            skills=random.choice(['Python', 'Java', 'React', 'JS', 'Ruby']),
        )
        consultant.visa_petition = True
        consultant.p_is_active = True
        consultant.pin = 123456789
        consultant.save()

        consultant_marketing = ConsultantMarketing.objects.create(
            cycle=1,
            status='open',
            consultant=consultant,
            primary_marketer=self.user,
            preferred_location=fake.city(),
            rtg=random.choice([True, False]),
            in_pool=random.choice([True, False]),
            previous_marketing_days=random.choice([0, 1, 2]),
        )
        consultant_marketing.teams.add(self.team)
        consultant_marketing.marketer.add(self.user)
        ConsultantRateRevision.objects.create(
            rate=45.0,
            start=date.today(),
            previous_rate=40.50,
            feedback=fake.text(),
            consultant=consultant,
        )
        ConsultantPOC.objects.create(
            poc=self.user,
            start=date.today(),
            poc_type='retention',
            consultant=consultant,
        )
        ConsultantPOC.objects.create(
            poc=self.user,
            start=date.today(),
            poc_type='recruiter',
            consultant=consultant,
        )
        ConsultantProfile.objects.create(
            education="phd",
            visa_type='h1b',
            title='Original',
            visa_end="2020-09-07",
            consultant=consultant,
            visa_start="2017-09-07",
            profile_owner=self.user,
            current_city='West Iowa',
            date_of_birth="1998-09-09",
        )
        WorkAuth.objects.create(
            is_current=True,
            consultant=consultant,
            visa_end="2022-12-12",
            visa_start="2018-11-11",
            visa_type=random.choice(['h1b', 'gc']),
        )
        ConsultantExit.objects.create(
            rehire=True,
            notice_period=6,
            type="resigned",
            legal_action=False,
            status="in_process",
            created_by=self.user,
            consultant=consultant,
            last_date="2022-09-09",
            resign_date="2020-03-09",
            cancel_reason="test text",
        )
        ConsultantExit.objects.create(
            rehire=True,
            notice_period=6,
            type="resigned",
            legal_action=False,
            status="in_process",
            created_by=self.user,
            consultant=consultant,
            last_date="2012-09-09",
            resign_date="2020-03-09",
            cancel_reason="test text",
        )
        return consultant_marketing

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
            rate=55,
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
                feedback_type="cfr",
                created_by=self.user,
                project_id=project.id,
                rating=random.choice([3, 4, 5]),
                consultant_id=marketing.consultant.id,
                description=f"test description {count}",
                department=random.choice(['Engineering', 'Legal', 'Marketing']),
            )
            Interview.objects.create(
                round=0,
                feedback=fake.text(),
                supervisor=self.user,
                submission=submission,
                tech_stack=fake.text(),
                description=fake.text(),
                guest_remark=fake.text(),
                call_details=fake.text(),
                coding_present=random.choice([True, False]),
                status=random.choice(['offer', 'scheduled', 'next_round']),
                screening_type=random.choice(['ip_screening', 'vendor_screening', 'interview']),
                interview_mode=random.choice(['skype', 'webex', 'dial_in', 'hangouts', 'video_call', 'voice_call']),
            )

            desc = f"Admin Demo added himself as support person"
            create_activity(project.id, 'projectsupport', self.user, desc, 'created')

        return project
