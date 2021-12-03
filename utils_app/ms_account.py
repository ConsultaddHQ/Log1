import os
import json
import requests

from log1.utils import write_exception, write_info


class MicrosoftAccount:
    def __init__(self):
        self.headers = self.get_ms_header()
        self.team = os.environ.get('consultadd_us_team_id')

    def get_ms_header(self):
        try:
            tenant_id = os.environ.get('tenant_id')
            client_id = os.environ.get('client_id')
            client_secret = os.environ.get('client_secret')
            scope = 'https%3A//graph.microsoft.com/.default'

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            payload = f'client_id={client_id}&client_secret={client_secret}&scope={scope}&grant_type=client_credentials'

            response = requests.request("POST", url, headers=headers, data=payload)
            data = json.loads(response.text.encode('utf8'))

            access_token = None
            if response.status_code == 200:
                access_token = data["access_token"]

            headers = {
                "Authorization": "bearer " + access_token,
                "Content-Type": "application/json"
            }
            return headers
        except Exception as error:
            write_exception(message=error)
            return None

    def create_account(self, data):
        try:
            payload = {
                "accountEnabled": True,
                "displayName": data['name'],
                "mailNickname": data['name'],
                "userPrincipalName": data['email'],
                "usageLocation": "IN",
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": "consultadd@123"
                }
            }
            url = f"https://graph.microsoft.com/v1.0/Users"
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 201:
                return data['id'], "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data), "error"
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    def disable_account(self, user_id):
        try:
            data = {
                "accountEnabled": False,
            }
            url = f"https://graph.microsoft.com/v1.0/Users/{user_id}"
            response = requests.patch(url, headers=self.headers, data=json.dumps(data))
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 201:
                return data['id'], "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data), "error"
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    def assign_licence(self, user_id):
        try:
            data = {
                "removeLicenses": [],
                "addLicenses": [
                    {
                        "disabledPlans": [],
                        "skuId": os.environ.get('licence_id')
                    }
                ],
            }
            url = f"https://graph.microsoft.com/v1.0/Users/{user_id}/assignLicense"
            response = requests.post(url, headers=self.headers, data=json.dumps(data))
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 200:
                return "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data)
        except Exception as error:
            write_exception(message=error)
            return str(error)

    def remove_licence(self, user_id):
        try:
            data = {
                "removeLicenses": [os.environ.get('licence_id')],
                "addLicenses": [
                    {
                        "disabledPlans": [],
                        "skuId": os.environ.get('licence_id')
                    }
                ],
            }
            url = f"https://graph.microsoft.com/v1.0/Users/{user_id}/assignLicense"
            response = requests.post(url, headers=self.headers, data=json.dumps(data))
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 200:
                return "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data)
        except Exception as error:
            write_exception(message=error)
            return str(error)

    def assign_team(self, user_id):
        try:
            data = {
                "roles": ['member'],
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users({user_id})"
            }
            url = f"https://graph.microsoft.com/v1.0/teams/{self.team}/members"
            response = requests.post(url, headers=self.headers, data=json.dumps(data))
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 201:
                return data['id'], "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data), "error"
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    def remove_member(self, member_id):
        try:
            if not member_id:
                return "Member id not found"

            url = f"https://graph.microsoft.com/v1.0/teams/{self.team}/members/{member_id}"
            response = requests.delete(url, headers=self.headers)
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 200:
                return "ok"
            else:
                write_info(message=data, function='create_account')
                return str(data)
        except Exception as error:
            write_exception(message=error)
            return str(error)
