import os
import json
import requests

from utils_app.calendar import get_ms_header
from log1.utils import write_exception, write_info


class MicrosoftAccount:
    def __init__(self):
        self.headers = get_ms_header()
        self.team = os.environ.get('consultadd_us_team_id')

    def create_account(self, data):
        try:
            payload = {
                "accountEnabled": True,
                "displayName": data['name'],
                "mailNickname": data['name'].split()[0],
                "userPrincipalName": data['email'],
                "usageLocation": "IN",
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": data['password']
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
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
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
