import os
import json
import os.path
import requests

from rest_framework.response import Response

from google.auth.exceptions import RefreshError
from googleapiclient import discovery
from google.oauth2.service_account import Credentials
from log1.utils import write_exception, write_info

SCOOPS = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/admin.directory.user']
SERVICE_ACCOUNT_FILE = 'calendar.json'
GRAPH_BASE_URL = 'https://graph.microsoft.com/v1.0/users/'


class GoogleCalendar:

    @staticmethod
    def calendar_con(calendar_id):
        credentials = Credentials.from_service_account_file(
            filename=SERVICE_ACCOUNT_FILE,
            scopes=SCOOPS,
            subject=calendar_id,
        )
        try:
            service = discovery.build('calendar', 'v3', credentials=credentials)
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
            data['attendees'] = [{'email': 'shivam.k@consultadd.com'}, {'email': 'shreyas.k@consultadd.com'},
                                 {'email': 'product@consultadd.com'}]
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
            'attendees': data["attendees"],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

    def book_calendar(self, data, calendar_id, request=None):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = "product@consultadd.com"
            service = self.calendar_con(calendar_id)
            event = self.get_body(data)
            try:
                event = service.events().insert(calendarId=calendar_id, body=event, sendUpdates='all').execute()
            except RefreshError:
                calendar = Calendar(request=request)
                cal_res, msg = calendar.book_ms_calendar(data, calendar_id)
                return cal_res, msg
            return event, "ok"
        except Exception as error:
            write_info(message=error, function='book_calendar')
            return str(error), "error"

    def update_calendar(self, event_id, data, calendar_id, request=None):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = "suman.m@consultadd.com"
            service = self.calendar_con(calendar_id)
            event = self.get_body(data)
            try:
                updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event,
                                                        sendUpdates='all').execute()
            except RefreshError:
                calendar = Calendar(request=request)
                cal_res, msg = calendar.update_ms_calendar(event_id, calendar_id, data)
                return cal_res, msg
            return updated_event, 'ok'
        except Exception as error:
            write_info(message=error, function='update_calendar')
            return str(error), "error"

    def get_interviews(self, user_emails, start, end, calendar_id):
        try:
            items = []
            for email in user_emails:
                data = {"id": email}
                items.append(data)
            service = self.calendar_con(calendar_id)
            time_min = start + 'T00:00:00-04:00'
            time_max = end + '-04:00'
            freebusy_query = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": "America/New_York",
                "items": items
            }
            res = service.freebusy().query(body=freebusy_query).execute()
            return res['calendars'], True
        except Exception as error:
            write_exception(message=error)
            return str(error), "error"

    def delete_calendar_booking(self, event_id, calendar_id, request):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = "suman.m@consultadd.com"
            service = self.calendar_con(calendar_id)
            try:
                service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates='all').execute()
            except RefreshError:
                calendar = Calendar(request=request)
                cal_res, msg = calendar.delete_ms_calendar(event_id, calendar_id)
                return cal_res, msg
            return True, "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error), "error"

    @staticmethod
    def formate_date(date):
        var = date['dateTime'].split(".")
        return "".join([var[0], "-00:00"])

    def get_calendar_schedule(self, data, request=None):
        try:
            items = []
            end = data['end']
            start = data['start']
            user_emails = data['user_emails']
            for email in user_emails:
                data = {"id": email}
                items.append(data)

            service = self.calendar_con("suman.m@consultadd.com")

            free_busy_query = {
                "timeMax": end, "timeMin": start,
                "items": items, "timeZone": 'US/Eastern'
            }
            res = service.freebusy().query(body=free_busy_query).execute()
            for email in user_emails:
                if "errors" in res['calendars'][email]:
                    payload = {
                        "start": start, "end": end, "emails": [email]
                    }
                    calendar = Calendar(request=request)
                    ms_res = calendar.get_ms_calendar_schedule(payload)
                    if ms_res.status_code != 200:
                        continue
                    else:
                        for item in ms_res.json()['value'][0].get('scheduleItems', []):
                            res['calendars'][email]['busy'].append(
                                {
                                    "start": self.formate_date(item.get('start')),
                                    "end": self.formate_date(item.get('end'))
                                }
                            )
            return res['calendars'], 'ok'
        except Exception as error:
            write_exception(message=error, request=request)
            return {"message": str(error)}, "error"


class Calendar:
    def __init__(self, request=None):
        self.request = request
        self.headers = self.get_ms_header(request)

    @staticmethod
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

    @staticmethod
    def calendar_ms_description(data):
        description = f'''

        <div><Strong>Calling Details</Strong></div> 
            {data.get('call_details', 'Not mentioned')} </br></br>

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

    def book_ms_calendar(self, data, calendar_id):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = 'product@consultadd.com'
            if not self.headers:
                return False, "error"
            event = self.get_ms_body(data)

            url = f"{GRAPH_BASE_URL}/{calendar_id}/events/"
            response = requests.post(url, headers=self.headers, data=event)
            data = json.loads(response.text.encode('utf-8'))
            if response.status_code == 201:
                return data, "ok"
            else:
                write_info(message=data, function='book_ms_calendar', request=self.request)
                return str(data), "error"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def update_ms_calendar(self, event_id, calendar_id, data):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = 'product@consultadd.com'
            if not self.headers:
                return False, "error"
            event = self.get_ms_body(data)

            url = f"{GRAPH_BASE_URL}/{calendar_id}/events/{event_id}/"
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
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def delete_ms_calendar(self, event_id, calendar_id):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = 'product@consultadd.com'
            if not self.headers:
                return False, "error"

            url = f"{GRAPH_BASE_URL}/{calendar_id}/events/{event_id}/"
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 204:
                return True, "ok"
            else:
                response_data = json.loads(response.text.encode('utf-8'))
                write_info(message=response_data, function='delete_ms_calendar', request=self.request)
                return False, "error"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return str(error), "error"

    def get_ms_calendar_schedule(self, data):
        try:
            headers = self.headers
            if not headers:
                return {"message": "Something went wrong", "error": "Unable to fetch calendar Token", "code": 400}
            payload = {
                "Schedules": data['emails'],
                "StartTime": {
                    "dateTime": data['start'],
                    "timeZone": "Eastern Standard Time"
                },
                "EndTime": {
                    "dateTime": data['end'],
                    "timeZone": " Eastern Standard Time"
                },
                "availabilityViewInterval": 15,
            }
            url = f"{GRAPH_BASE_URL}/product@consultadd.com/calendar/getschedule"
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            return response
        except Exception as error:
            write_exception(message=error, request=self.request)
            return Response({"message": "Email not found"}, status=400)
