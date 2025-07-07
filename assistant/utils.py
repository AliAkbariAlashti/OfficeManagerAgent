import os
from datetime import datetime, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from django.utils import timezone
from .models import Meeting, Task
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_PATH = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')

def get_calendar_service():
    creds = Credentials.from_authorized_user_file(CREDENTIALS_PATH, SCOPES)
    return build('calendar', 'v3', credentials=creds)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_request(user_input):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a personal assistant for a CEO, responding in formal and polite Persian. Your tasks include managing meetings (create, edit, cancel, report) and daily tasks."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content

def create_meeting(title, date, time_str, location="", attendees="", notes=""):
    try:
        meeting_time = timezone.datetime.strptime(time_str, '%H:%M').time()
        meeting = Meeting.objects.create(
            title=title,
            date=date,
            time=meeting_time,
            location=location,
            attendees=attendees,
            notes=notes
        )

        service = get_calendar_service()
        event = {
            'summary': title,
            'location': location,
            'description': notes,
            'start': {
                'dateTime': f'{date}T{time_str}:00',
                'timeZone': 'Asia/Tehran',
            },
            'end': {
                'dateTime': f'{date}T{time_str}:00',
                'timeZone': 'Asia/Tehran',
            },
            'attendees': [{'email': email.strip()} for email in attendees.split(',') if email.strip()],
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return f"Meeting '{title}' created successfully."
    except Exception as e:
        return f"Error creating meeting: {str(e)}"

def get_meetings_by_date_range(start_date, end_date):
    meetings = Meeting.objects.filter(date__range=[start_date, end_date])
    if not meetings:
        return "No meetings found in this date range."
    result = "Meetings:\n"
    for meeting in meetings:
        result += f"- {meeting.title} on {meeting.date} at {meeting.time}, location: {meeting.location}\n"
    return result

def find_free_slots(date):
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=f'{date}T00:00:00+03:30',
        timeMax=f'{date}T23:59:59+03:30',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    
    busy_slots = [(event['start']['dateTime'], event['end']['dateTime']) for event in events]
    free_slots = []
    current_time = datetime.strptime(f'{date} 09:00', '%Y-%m-%d %H:%M')
    end_of_day = datetime.strptime(f'{date} 17:00', '%Y-%m-%d %H:%M')
    
    while current_time < end_of_day:
        slot_end = (current_time + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S+03:30')
        current_time_str = current_time.strftime('%Y-%m-%dT%H:%M:%S+03:30')
        if not any(start <= current_time_str < end for start, end in busy_slots):
            free_slots.append(current_time.strftime('%H:%M'))
        current_time += timezone.timedelta(hours=1)
    
    return free_slots if free_slots else "No free slots found on this date."
