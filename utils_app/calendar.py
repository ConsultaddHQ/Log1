import os
import json
import os.path
import requests
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from log1.utils import write_exception, write_info

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendar:

    @staticmethod
    def calendar_con():
        creeds = None
        if os.path.exists(os.environ.get("TOKEN")):
            creeds = Credentials.from_authorized_user_file(os.environ.get("TOKEN"), SCOPES)
        if not creeds or not creeds.valid:
            if creeds and creeds.expired and creeds.refresh_token:
                creeds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.environ.get("KEY_FILE"), SCOPES)
                creeds = flow.run_local_server(port=0)
            with open(os.environ.get("TOKEN"), 'w') as token:
                token.write(creeds.to_json())
        try:
            service = build('calendar', 'v3', credentials=creeds)
            return service
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    @staticmethod
    def calendar_description(data):
        description = f'''
        <strong>Calling Details</strong>
            {data["call_details"]}

        <strong>Marketer Name - {data["user"].employee_name}</strong>
        <strong>Employer - {data["submission"].employer}</strong>

        <strong>consultant Details: </strong>

            Name - {data["consultant"].name}
            DOB - {data["submission"].date_of_birth}
            SSN - {data["consultant"].ssn}
            VISA - {data["submission"].visa_type}
            Visa Start - {data["submission"].visa_start}
            Visa End - {data["submission"].visa_end}

            Skype id - {data["consultant"].skype}

            Education - {data["submission"].education}

        <strong>Position Details:</strong>

            Location = {data["lead"].city}
            Job Title - {data["lead"].job_title}
            Client Name - {data["submission"].client}

        <strong>Extra details:</strong> 
            {data["description"]}

        <strong>Job Description:</strong>
            {data["lead"].job_desc}

        '''
        return description

    def get_body(self, data):
        description = self.calendar_description(data)
        if os.environ.get('ENV', 'local') != 'prod':
            data['attendees'] = [{'email': 'shivam.k@consultadd.com'}, {'email': 'shreyas.k@consultadd.com'}]
        return {
            'summary': data["summary"],
            'description': description,

            'start': {
                'dateTime': data["start"],
                'timeZone': 'America/New_York',
            },

            'end': {
                'dateTime': data["end"],
                'timeZone': 'America/New_York',
            },

            'recurrence': [
                'RRULE:FREQ=DAILY;COUNT=1'
            ],

            'attendees': data["attendees"],

            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

    def book_calendar(self, data):
        try:
            service = self.calendar_con()
            event = self.get_body(data)
            event = service.events().insert(calendarId=os.environ.get('LOG1_CALENDER_ID'), body=event, sendUpdates='all').execute()
            return event, "ok"
        except Exception as error:
            write_info(message=error, function='book_calendar')
            return str(error), "error"

    def update_calendar(self, event_id, data):
        try:
            service = self.calendar_con()
            event = self.get_body(data)
            updated_event = service.events().update(calendarId=os.environ.get('LOG1_CALENDER_ID'), eventId=event_id, body=event,
                                                    sendUpdates='all').execute()
            return updated_event, 'ok'
        except Exception as error:
            write_info(message=error, function='update_calendar')
            return str(error), "error"

    def get_interviews(self, user_emails, start, end):
        try:
            items = []
            for email in user_emails:
                data = {"id":email}
                items.append(data)
            service = self.calendar_con()
            time_min = start + 'T00:00:00-04:00'
            time_max = end + '-04:00'
            freebusy_query = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": "America/New_York",
                "items": items
            }
            res = service.freebusy().query(body=freebusy_query).execute()
            return res['calendars'],True
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    def delete_calendar_booking(self, event_id, request):
        try:
            service = self.calendar_con()
            service.events().delete(calendarId=os.environ.get('LOG1_CALENDER_ID'), eventId=event_id, sendUpdates='all').execute()
            return True, "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error), "error"


def get_ms_header(request=None):
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
            "Authorization": "bearer " + access_token if access_token else "bearer ",
            "Content-Type": "application/json"
        }
        return headers
    except Exception as error:
        write_exception(message=error, request=request)
        return None


class Calendar:
    def __init__(self, request=None):
        self.request = request
        self.headers = get_ms_header(request)

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
                "DateTime": str(data["start"]),
                "TimeZone": "Eastern Standard Time"
            },
            "End": {
                "DateTime": str(data["end"]),
                "TimeZone": "Eastern Standard Time"
            },
            "Attendees": attendees
        })

    def book_ms_calendar(self, data):
        try:
            if os.environ.get('ENV', 'local') == 'prod':
                if not self.headers:
                    return False, "error"
                event = self.get_ms_body(data)

                url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/"
                response = requests.post(url, headers=self.headers, data=event)
                data = json.loads(response.text.encode('utf-8'))
                if response.status_code == 201:
                    return data, "ok"
                else:
                    write_info(message=data, function='book_ms_calendar', request=self.request)
                    return str(data), "error"
            return {"id": "Calendar ID"}, "ok"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def update_ms_calendar(self, event_id, data):
        try:
            if os.environ.get('ENV', 'local') == 'prod':
                if not self.headers:
                    return False, "error"

                event = self.get_ms_body(data)
                url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
                response = requests.patch(url, headers=self.headers, data=event)
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
            return {"id": "Calendar ID"}, "booked"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def delete_ms_calendar(self, event_id):
        try:
            if os.environ.get('ENV', 'local') == 'prod':
                if not self.headers:
                    return False, "error"

                url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
                response = requests.delete(url, headers=self.headers)
                if response.status_code == 204:
                    return True, "ok"
                else:
                    response_data = json.loads(response.text.encode('utf-8'))
                    write_info(message=response_data, function='delete_ms_calendar', request=self.request)
                    return False, "error"
            return True, "ok"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"


def get_profile_picture(user):
    ca_logo_url = f"{os.environ.get('base_domain', 'http://localhost:8000')}/media/avatar/ca.png"
    try:
        file_path = f"media/avatar/{user.employee_id}.png"
        if os.path.exists(file_path):
            return f"{os.environ.get('base_domain', 'http://localhost:8000')}/{file_path}"

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
