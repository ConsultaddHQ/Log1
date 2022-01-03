from datetime import date, timedelta
from rest_framework.test import APITestCase, APIClient

from employee.models import User, Team, Role
from consultant.models import Consultant, ConsultantMarketing
from marketing.models import Submission, Lead, VendorCompany, VendorContact


class Setup:
    def __init__(self):
        self.team = Team.objects.create(name="Boto3")
        role = Role.objects.create(name="marketer")
        self.user = User.objects.create(
            username=8000,
            team=self.team,
            employee_id=8000,
            password='consultadd',
            email='demo@log1.com',
            employee_name='Demo',
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
            username=8001,
            team=self.team,
            employee_id=8001,
            password='consultadd',
            email='admin@log1.com',
            employee_name='Admin Demo',
        )
        admin_user.role.add(admin_role)
        return admin_user


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
