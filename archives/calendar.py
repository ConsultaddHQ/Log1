import os
import httplib2
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials


class GoogleCalendar:

    @staticmethod
    def calendar_con():
        refresh_token = os.environ.get('REFRESH_TOKEN')
        expires_in = 3599
        token = os.environ.get('ACCESS_TOKEN')
        credential = OAuth2Credentials(token, os.environ.get('CLIENT_ID'),
                                       os.environ.get('CLIENT_SECRET'), refresh_token, expires_in,
                                       'https://accounts.google.com/o/oauth2/token', "")

        http = httplib2.Http()
        credential.authorize(http)
        service = build('calendar', 'v3', http=http)
        return service

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
        service = self.calendar_con()
        event = self.get_body(data)
        event = service.events().insert(calendarId='admin@log1.com', body=event, sendUpdates='all').execute()
        return event

    def update_calendar(self, event_id, data):
        service = self.calendar_con()
        event = self.get_body(data)
        updated_event = service.events().update(calendarId='admin@log1.com', eventId=event_id, body=event,
                                                sendUpdates='all').execute()
        return updated_event['id']

    def get_interviews(self, data):
        service = self.calendar_con()
        page_token = None
        calendar_data = []
        time_min = data["start"] + '06:00:00-04:00'
        time_max = data["end"] + '23:59:00-04:00'
        while True:
            events = service.events().list(calendarId=data["email"],
                                           pageToken=page_token,
                                           singleEvents=True,
                                           orderBy="startTime",
                                           timeMin=time_min,
                                           timeMax=time_max
                                           ).execute()
            visibility = True
            for event in events["items"]:
                if "visibility" in event:
                    visibility = False
                    data = {
                        "id": event["id"],
                        "visibility": False,
                        "updated": event["updated"],
                        "end": event["end"]["dateTime"] if "dateTime" in event["end"] else event["end"]["date"],
                        "start": event["start"]["dateTime"] if "dateTime" in event["start"] else event["start"]["date"],
                    }
                else:
                    data = {
                        "id": event["id"],
                        "visibility": True,
                        "created": event["created"],
                        "updated": event["updated"],
                        "end": event["end"]["dateTime"] if "dateTime" in event["end"] else event["end"]["date"],
                        "start": event["start"]["dateTime"] if "dateTime" in event["start"] else event["start"]["date"],
                        "title": event["summary"] if "summary" in event else "",
                        "description": event["description"] if "description" in event else "",
                        "attendees": [i["email"] for i in event["attendees"]] if "attendees" in event else [],
                        "attachments": [{"fileUrl": i["fileUrl"], "title": i["title"]} for i in
                                        event["attachments"]] if "attachments" in event else []
                    }
                calendar_data.append(data)
            page_token = events.get('nextPageToken')
            if not page_token:
                return calendar_data, visibility

    def delete_calendar_booking(self, event_id):
        service = self.calendar_con()
        service.events().delete(calendarId='admin@log1.com', eventId=event_id, sendUpdates='all').execute()
