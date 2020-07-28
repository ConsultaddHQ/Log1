import os
import json
import requests
import httplib2
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials


def create_ms_token():
    tenant_id = os.environ.get('tenant_id')
    client_id = os.environ.get('client_id')
    client_secret = os.environ.get('client_secret')
    scope = 'https%3A//graph.microsoft.com/.default'

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = f'client_id={client_id}&client_secret={client_secret}&scope={scope}&grant_type=client_credentials'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.request("POST", url, headers=headers, data=payload)

    data = json.loads(response.text.encode('utf8'))
    access_token = None
    if response.status_code == 200:
        access_token = data["access_token"]
    return access_token


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


def book_ms_calendar(data):
    try:
        token = create_ms_token()
        description = calendar_ms_description(data)
        attendees = []
        for i in data['attendees']:
            attendees.append({
                "EmailAddress": {
                    "Address": i['email'],
                },
            })

        event = json.dumps({
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
        headers = {
            "Authorization": "bearer " + token,
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/"
        response = requests.post(url, headers=headers, data=event)
        if response.status_code == 201:
            return json.loads(response.text.encode('utf-8'))
        return False
    except Exception as error:
        print(error)
        return False


def update_ms_calendar(event_id, data):
    try:
        token = create_ms_token()
        description = calendar_ms_description(data)
        attendees = []
        for i in data['attendees']:
            attendees.append({
                "EmailAddress": {
                    "Address": i['email'],
                },
            })

        event = json.dumps({
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
        headers = {
            "Authorization": "bearer " + token,
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
        response = requests.patch(url, headers=headers, data=event)
        if response.status_code == 200:
            return json.loads(response.text.encode('utf-8'))
        return False
    except Exception as error:
        print(error)
        return False


def delete_ms_calendar(event_id):
    try:
        token = create_ms_token()
        headers = {
            "Authorization": "bearer " + token,
            "Content-Type": "application/json"
        }
        url = f"https://graph.microsoft.com/v1.0/Users/{os.environ.get('user_id')}/events/{event_id}/"
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            return True
        return False
    except Exception as error:
        print(error)
        return False


def get_user_id(email):
    token = create_ms_token()
    headers = {
        "Authorization": "bearer " + token,
        "Content-Type": "application/json"
    }
    url = f"https://graph.microsoft.com/v1.0/users/?$select=displayName,id&$filter=identities/any(c:c/issuerAssignedId eq '{email}')"
    response = requests.get(url, headers=headers)
    data = json.loads(response.text.encode('utf-8'))
    return data


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

        'attendees': data["attendees"],

        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    event = service.events().insert(calendarId='admin@log1.com', body=event, sendUpdates='all').execute()
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

        'attendees': data["attendees"],

        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    updated_event = service.events().update(calendarId='admin@log1.com', eventId=event_id, body=event,
                                            sendUpdates='all').execute()
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


def delete_calendar_booking(event_id):
    service = calendar_con()
    service.events().delete(calendarId='admin@log1.com', eventId=event_id, sendUpdates='all').execute()
