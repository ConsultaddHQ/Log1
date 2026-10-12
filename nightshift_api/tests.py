from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api_key.models import APIKey
from consultant.models import Consultant, ConsultantMarketing
from employee.models import Team, User
from marketing.models import Lead, Submission


class BenchConsultantSnapshotTests(APITestCase):
    url = "/api/nightshift/bench-consultants/"

    def setUp(self):
        self.team = Team.objects.create(name="NightShift Test Team")
        self.marketer = User.objects.create(
            employee_id=71001,
            username=71001,
            email="nightshift-marketer@example.com",
            employee_name="NightShift Marketer",
            team=self.team,
        )
        self.consultant = Consultant.objects.create(
            name="Bench Consultant",
            email="bench-consultant@example.com",
            phone_no="555-0100",
            ssn="sensitive-ssn",
            date_of_birth="1980-01-01",
            status="on_bench",
        )
        self.marketing = ConsultantMarketing.objects.create(
            consultant=self.consultant,
            primary_marketer=self.marketer,
            status="open",
        )
        self.marketing.marketer.add(self.marketer)

        lead = Lead.objects.create(
            job_desc="A sufficiently long job description for this test submission.",
            owner=self.marketer,
        )
        now = timezone.now()
        completed_submission = Submission.objects.create(
            consultant_marketing=self.marketing,
            lead=lead,
            created_by=self.marketer,
            employer="Sensitive Employer",
            email="private@example.com",
            phone="555-0199",
            rate=999,
            visa_type="sensitive-visa",
            is_complete=True,
        )
        incomplete_submission = Submission.objects.create(
            consultant_marketing=self.marketing,
            lead=lead,
            created_by=self.marketer,
            employer="Sensitive Employer",
            is_complete=False,
        )
        previous_submission = Submission.objects.create(
            consultant_marketing=self.marketing,
            lead=lead,
            created_by=self.marketer,
            employer="Sensitive Employer",
            is_complete=True,
        )
        Submission.objects.filter(id=completed_submission.id).update(created=now)
        Submission.objects.filter(id=incomplete_submission.id).update(created=now)
        Submission.objects.filter(id=previous_submission.id).update(created=now - timedelta(days=14))
        self.api_key, self.raw_key = APIKey.objects.create_key(name="nightshift-read-only")

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION="Api-Key {}".format(self.raw_key))

    def test_requires_a_valid_api_key(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION="Api-Key invalid")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_only_owned_bench_data_and_weekly_completed_count(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [{
            "consultant_id": self.consultant.id,
            "consultant_name": "Bench Consultant",
            "marketer_id": self.marketer.id,
            "marketer_name": "NightShift Marketer",
            "bench_status": "on_bench",
            "weekly_completed_submission_count": 1,
        }])
        forbidden_fields = {
            "email", "phone", "phone_no", "date_of_birth", "visa", "visa_type",
            "ssn", "rate", "resume", "employer", "client",
        }
        self.assertTrue(forbidden_fields.isdisjoint(response.data["data"][0]))

    def test_accepts_existing_public_api_key_header(self):
        self.client.credentials(HTTP_API_KEY="Token {}".format(self.raw_key))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mutating_methods_are_rejected(self):
        self.authenticate()
        before = Submission.objects.count()

        for method in ("post", "put", "patch", "delete"):
            response = getattr(self.client, method)(self.url, data={})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(Submission.objects.count(), before)
