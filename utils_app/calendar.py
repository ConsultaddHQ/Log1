import httplib2
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials


def calendar_con():
    refresh_token = "1/pC5KN2aCTRx_R4tS8xEGlUCZx6LI4pjwkDo71bhgwrw"
    expires_in = 3599
    token = "ya29.Glv2BgSkQqLfsWiPn3_S1dZTx_TJPIQBcGsCWcBTmZife20z7ik6b7IzNkUv2iWlc9UaYbEgj4e8I" \
            "Tkk5WAKYFUz1wVKk1xokIWHbe9GJ-XU7uPo57NTFIUELRLN"
    credential = OAuth2Credentials(token, "414060049848-lhccvdlscbmoap54i1qk5333oobsfbf3.apps.googleusercontent.com",
                                   "Kj-4GHm_eRdIKq_Vrlh7Ek78", refresh_token, expires_in,
                                   'https://accounts.google.com/o/oauth2/token', "")

    http = httplib2.Http()
    credential.authorize(http)
    service = build('calendar', 'v3', http=http)
    return service


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


def book_calendar(data):
    service = calendar_con()
    description = calendar_description(data)

    event = {
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

        # 'attendees': data["attendees"],
        'attendees': [],

        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    event = service.events().insert(calendarId='admin@log1.com', body=event).execute()
    return event


def update_calendar(event_id, data):
    service = calendar_con()
    description = calendar_description(data)
    event = {
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

        # 'attendees': data["attendees"],
        'attendees': [],

        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    updated_event = service.events().update(calendarId='admin@log1.com', eventId=event_id, body=event).execute()
    return updated_event['id']


def get_interviews(data):
    service = calendar_con()
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
                    "updated": event["updated"],
                    "start": event["start"]["dateTime"],
                    "end": event["end"]["dateTime"],
                }
            else:
                data = {
                    "id": event["id"],
                    "title": event["summary"] if "summary" in event else "",
                    "description": event["description"] if "description" in event else "",
                    "created": event["created"],
                    "updated": event["updated"],
                    "start": event["start"]["dateTime"],
                    "end": event["end"]["dateTime"],
                    "attendees": [i["email"] for i in event["attendees"]] if "attendees" in event else [],
                    "attachments": [{"fileUrl": i["fileUrl"], "title": i["title"]} for i in
                                    event["attachments"]] if "attachments" in event else []
                }
            calendar_data.append(data)
        page_token = events.get('nextPageToken')
        if not page_token:
            return calendar_data, visibility


def delete_calendar_booking(event_id):
    service = calendar_con()
    service.events().delete(calendarId='admin@log1.com', eventId=event_id).execute()
