import os
import json
import requests

from log1.utils import write_exception, write_info


class Calendar:
    def __init__(self, request=None):
        self.request = request
        self.headers = self.get_ms_header()

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
            write_exception(message=error, request=self.request)
            return None

    @staticmethod
    def calendar_ms_description(data):
        description = f'''

        <div><Strong>Calling Details</Strong></div> 
            {data["call_details"]} </br></br>

        <div><Strong>Marketer Name -</Strong> {data["user"].employee_name}</div> 
        <div><Strong>Employer - </Strong>{data["submission"].employer}</div> </br>

        <div><Strong>consultant Details:</Strong> </div>

           <Strong> Name -</Strong> {data["consultant"].name}  </br>
           <Strong> DOB - </Strong>{data["submission"].date_of_birth}</br> 
            <Strong>SSN -</Strong> {data["consultant"].ssn} </br>
            <Strong>VISA - </Strong>{data["submission"].visa_type}</br> 
            <Strong>Visa Start -</Strong> {data["submission"].visa_start}</br> 
            <Strong>Visa End -</Strong>{data["submission"].visa_end}</br>

           <Strong> Skype id </Strong>- {data["consultant"].skype}</br>

            <Strong>Education </Strong>- {data["submission"].education}</br></br>

        <div><Strong>Position Details:</Strong></div>

           <Strong> Location - </Strong>{data["lead"].city}</br>
           <Strong> Job Title - </Strong>{data["lead"].job_title}</br>
           <Strong> Client Name - </Strong>{data["submission"].client}</br></br>

        <div><Strong>Extra details:</Strong> </div>
            {data["description"]}</br></br>

        <div><Strong>Job Description:</Strong></div>
            {data["lead"].job_desc}</br></br>

        '''
        return description

    def get_ms_body(self, data):
        description = self.calendar_ms_description(data)
        attendees = []
        for i in data['attendees']:
            attendees.append({
                "EmailAddress": {
                    "Address": i['email'],
                },
            })

        return json.dumps({
            "Subject": data["summary"],
            "Body": {
                "ContentType": "HTML",
                "Content": description
            },
            "Start": {
                "DateTime": data["start"],
                "TimeZone": "Eastern Standard Time"
            },
            "End": {
                "DateTime": data["end"],
                "TimeZone": "Eastern Standard Time"
            },
            "Attendees": attendees
        })

    def book_ms_calendar(self, data):
        try:
            headers = self.get_ms_header()
            if not headers:
                return False, "error"
            event = self.get_ms_body(data)

            url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/"
            response = requests.post(url, headers=headers, data=event)
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 201:
                return data, "ok"
            else:
                write_info(message=data, function='book_ms_calendar', request=self.request)
                return str(data), "error"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def update_ms_calendar(self, event_id, data):
        try:
            headers = self.get_ms_header()
            if not headers:
                return False, "error"

            event = self.get_ms_body(data)
            url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
            response = requests.patch(url, headers=headers, data=event)
            response_data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 200:
                return response_data, "updated"
            if response.status_code == 404:
                response_data, msg = self.book_ms_calendar(data)
                if msg == 'ok':
                    return response_data, "booked"
                else:
                    write_info(message=response_data, function='update_ms_calendar', request=self.request)
                    return str(response_data), "error"
            else:
                write_info(message=response_data, function='update_ms_calendar', request=self.request)
                return str(response_data), "error"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def delete_ms_calendar(self, event_id):
        try:
            headers = self.get_ms_header()
            if not headers:
                return False, "error"

            url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                return True, "ok"
            else:
                response_data = json.loads(response.text.encode('utf-8'))
                write_info(message=response_data, function='delete_ms_calendar', request=self.request)
                return False, "error"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"


def get_profile_picture(user):
    ca_logo_url = f"{os.environ.get('base_domain', 'http://localhost:8000')}/media/avatar/ca.png"
    try:
        file_path = f"media/avatar/{user.employee_id}.png"
        if os.path.exists(file_path):
            return file_path

        obj = Calendar()
        headers = obj.headers
        url = f"https://graph.microsoft.com/v1.0/users/{user.email}/photo/$value"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return f"{os.environ.get('base_domain', 'http://localhost:8000')}/{file_path}"
        return ca_logo_url
    except Exception as error:
        write_info(message=error, function='get_profile_picture')
        return ca_logo_url
