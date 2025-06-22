# google_calendar_service.py

import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
from config import Config


class GoogleCalendarService:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar', 
            'https://www.googleapis.com/auth/forms', 
            'https://www.googleapis.com/auth/drive' 
        ]

    def get_authorization_url(self):
        """Get Google OAuth URL for calendar access"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": Config.GOOGLE_CLIENT_ID,
                    "client_secret": Config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth", 
                    "token_uri": "https://oauth2.googleapis.com/token", 
                    "redirect_uris": [Config.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
        authorization_url, _ = flow.authorization_url(prompt='consent')
        return authorization_url, flow

    def exchange_code_for_tokens(self, code, flow):
        """Exchange authorization code for tokens"""
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return credentials

    def build_service(self, credentials):
        """Build Google Calendar service using credentials"""
        return build('calendar', 'v3', credentials=credentials)

    def get_available_slots(self, doctor, start_date, end_date, duration_minutes=30):
        """Get available appointment slots for a doctor"""
        credentials = self._get_doctor_credentials(doctor)
        service = self.build_service(credentials)

        busy_query = {
            'timeMin': start_date.isoformat(),
            'timeMax': end_date.isoformat(),
            'items': [{'id': doctor['google_calendar_id']}]
        }

        busy_times = service.freebusy().query(body=busy_query).execute()
        busy_periods = busy_times['calendars'][doctor['google_calendar_id']]['busy']

        working_hours = json.loads(doctor.get('working_hours', '{}')) or {
            'monday': {'start': '09:00', 'end': '17:00'},
            'tuesday': {'start': '09:00', 'end': '17:00'},
            'wednesday': {'start': '09:00', 'end': '17:00'},
            'thursday': {'start': '09:00', 'end': '17:00'},
            'friday': {'start': '09:00', 'end': '17:00'}
        }

        available_slots = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            day_name = current_date.strftime('%A').lower()
            if day_name in working_hours:
                day_hours = working_hours[day_name]
                start_time = datetime.combine(current_date,
                                              datetime.strptime(day_hours['start'], '%H:%M').time())
                end_time = datetime.combine(current_date,
                                            datetime.strptime(day_hours['end'], '%H:%M').time())

                current_slot = start_time
                while current_slot + timedelta(minutes=duration_minutes) <= end_time:
                    slot_end = current_slot + timedelta(minutes=duration_minutes)
                    is_available = True
                    for busy_period in busy_periods:
                        busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                        if (current_slot < busy_end and slot_end > busy_start):
                            is_available = False
                            break
                    if is_available:
                        available_slots.append(current_slot)
                    current_slot += timedelta(minutes=duration_minutes)
            current_date += timedelta(days=1)

        return available_slots

    def create_appointment(self, doctor, patient, appointment_datetime, duration_minutes, reason):
        """Create a new appointment in Google Calendar"""
        credentials = self._get_doctor_credentials(doctor)
        service = self.build_service(credentials)

        event = {
            'summary': f'Appointment: {patient["name"]}',
            'description': f'Patient: {patient["name"]}\nReason: {reason}\nContact: {patient["email"]}, {patient["phone"]}',
            'start': {
                'dateTime': appointment_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': (appointment_datetime + timedelta(minutes=duration_minutes)).isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': patient['email']},
                {'email': doctor['email']}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        created_event = service.events().insert(calendarId=doctor['google_calendar_id'], body=event).execute()
        return created_event['id']

    def _get_doctor_credentials(self, doctor):
        """Stub for getting stored credentials - implement with token storage"""
        # In production, retrieve from database or secure storage
        return None