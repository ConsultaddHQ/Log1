import os
import json
import os.path
import requests
from googleapiclient import discovery
from google.oauth2.service_account import Credentials
from log1.utils import write_exception, write_info
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow

SCOOPS = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/admin.directory.user']
SERVICE_ACCOUNT_FILE = 'calendar.json'

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
            'attendees': data["attendees"],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

    def book_calendar(self, data, calendar_id):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = "suman.m@consultadd.com"
            service = self.calendar_con(calendar_id)
            event = self.get_body(data)
            event = service.events().insert(calendarId=calendar_id, body=event, sendUpdates='all').execute()
            return event, "ok"
        except Exception as error:
            write_info(message=error, function='book_calendar')
            return str(error), "error"

    def update_calendar(self, event_id, data, calendar_id):
        try:
            if os.environ.get('ENV', 'local') != 'prod':
                calendar_id = "suman.m@consultadd.com"
            service = self.calendar_con(calendar_id)
            event = self.get_body(data)
            updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event,
                                                    sendUpdates='all').execute()
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
            service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates='all').execute()
            return True, "ok"
        except Exception as error:
            write_exception(message=error, request=request)
            return str(error), "error"