from twilio.rest import Client
from datetime import datetime
from config import Config

class NotificationService:
    def __init__(self):
        self.twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        
    async def send_whatsapp_message(self, to_number: str, message: str):
        """Send WhatsApp message"""
        try:
            message = self.twilio_client.messages.create(
                body=message,
                from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{to_number}"
            )
            return message.sid
        except Exception as e:
            print(f"WhatsApp sending failed: {e}")
            return None

    async def send_appointment_confirmation(self, appointment, patient, doctor):
        await self.send_sms_confirmation(appointment, patient, doctor)

    async def send_sms_confirmation(self, appointment, patient, doctor):
        message_body = f"""
Appointment Confirmed!
Doctor: Dr. {doctor['name']}
Date: {appointment['scheduled_datetime']}
Time: {appointment['scheduled_datetime']}
Duration: {appointment['duration_minutes']} minutes
Need to reschedule? Reply RESCHEDULE
Questions? Call (555) 123-4567
        """.strip()
        try:
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=patient['phone']
            )
            return message.sid
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return None

    async def send_reminder(self, appointment, patient, doctor, hours_before):
        message_body = f"""
Reminder: You have an appointment tomorrow
Doctor: Dr. {doctor['name']}
Date: {appointment['scheduled_datetime']}
Time: {appointment['scheduled_datetime']}
Reply CONFIRM to confirm or RESCHEDULE to change
        """.strip()
        try:
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=patient['phone']
            )
            return message.sid
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return None

    async def send_form_reminder(self, appointment, patient):
        message_body = """
Thank you for your visit!
Please share your feedback: https://forms.google.com/appointment-feedback/ 
        """
        try:
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=patient['phone']
            )
            return message.sid
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return None