from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio

class AppointmentScheduler:
    def __init__(self, notification_service):
        self.scheduler = AsyncIOScheduler()
        self.notification_service = notification_service

    def start(self):
        self.scheduler.add_job(self.send_reminders, CronTrigger(minute=0), id='send_reminders')
        self.scheduler.add_job(self.send_post_appointment_forms, CronTrigger(minute='*/30'), id='send_forms')
        self.scheduler.start()

    async def send_reminders(self):
        now = datetime.utcnow()
        tomorrow = now + timedelta(hours=24)

        # Get appointments from Supabase
        response = supabase.table("appointments").select("*").filter(
            "scheduled_datetime", "between", [tomorrow - timedelta(minutes=30), tomorrow + timedelta(minutes=30)]
        ).filter("status", "eq", "scheduled").execute()
        appointments = response.data

        for appointment in appointments:
            patient = supabase.table("patients").select("*").eq("id", appointment["patient_id"]).single().execute().data
            doctor = supabase.table("doctors").select("*").eq("id", appointment["doctor_id"]).single().execute().data
            await self.notification_service.send_reminder(appointment, patient, doctor, 24)

    async def send_post_appointment_forms(self):
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        response = supabase.table("appointments").select("*").filter(
            "status", "eq", "completed"
        ).filter("form_sent", "eq", False).filter(
            "scheduled_datetime", "gte", cutoff_time.isoformat()
        ).execute()
        appointments = response.data

        for appointment in appointments:
            patient = supabase.table("patients").select("*").eq("id", appointment["patient_id"]).single().execute().data
            form_url = await self.create_post_appointment_form(appointment)
            if form_url:
                await self.send_form_to_patient(appointment, patient, form_url)
                supabase.table("appointments").update({"form_sent": True}).eq("id", appointment["id"]).execute()

    async def create_post_appointment_form(self, appointment):
        return f"https://forms.google.com/appointment-feedback/{appointment['id']}" 

    async def send_form_to_patient(self, appointment, patient, form_url):
        message_body = f"""
Thank you for your recent appointment.
We'd appreciate your feedback: {form_url}
        """
        try:
            self.twilio_client.messages.create(
                body=message_body,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=patient['phone']
            )
        except Exception as e:
            print(f"Form SMS failed: {e}")