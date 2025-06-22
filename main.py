from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from datetime import datetime
from twilio.twiml.messaging_response import MessagingResponse
from fastapi import Form

app = FastAPI(title="AI Appointment Management System")

# Initialize services
from google_calander_service import GoogleCalendarService
from ai_agent import AIAppointmentAgent
from notification_service import NotificationService
from scheduler import AppointmentScheduler

calendar_service = GoogleCalendarService()
ai_agent = AIAppointmentAgent()
notification_service = NotificationService()

# Pydantic models
class PatientCreate(BaseModel):
    name: str
    email: str
    phone: str
    preferred_communication: str = "sms"

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_datetime: datetime
    appointment_type: str
    reason: str
    duration_minutes: int = 30

class ChatMessage(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat_with_ai(chat_data: ChatMessage):
    # Fetch doctors
    doctors_response = supabase.table("doctors").select("*").execute()
    doctors = doctors_response.data

    ai_response = ai_agent.process_message(chat_data.user_id, chat_data.message, doctors)

    if ai_response.get('action_needed') == 'get_availability':
        context = ai_agent.conversation_context.get(chat_data.user_id, {})
        collected_info = context.get('collected_info', {})
        if 'doctor_name' in collected_info:
            doctor_response = supabase.table("doctors").select("*").ilike("name", f"%{collected_info['doctor_name']}%").limit(1).execute()
            if doctor_response.data:
                doctor = doctor_response.data[0]
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=14)
                available_slots = calendar_service.get_available_slots(doctor, start_date, end_date)
                slot_options = [{"datetime": s.isoformat(), "display": s.strftime("%A, %B %d at %I:%M %p")} for s in available_slots[:10]]
                ai_response['available_slots'] = slot_options

    elif ai_response.get('action_needed') == 'book_appointment':
        context = ai_agent.conversation_context.get(chat_data.user_id, {})
        collected_info = context.get('collected_info', {})
        try:
            # Create or get patient
            patient_response = supabase.table("patients").select("*").eq("email", collected_info['email']).single().execute()
            if patient_response.data:
                patient = patient_response.data
            else:
                new_patient = {
                    "name": collected_info['name'],
                    "email": collected_info['email'],
                    "phone": collected_info['phone'],
                    "preferred_communication": collected_info.get('preferred_communication', 'sms')
                }
                patient_response = supabase.table("patients").insert(new_patient).execute()
                patient = patient_response.data[0]

            # Get doctor
            doctor_response = supabase.table("doctors").select("*").ilike("name", f"%{collected_info['doctor_name']}%").limit(1).execute()
            doctor = doctor_response.data[0]

            appointment_datetime = datetime.fromisoformat(collected_info['selected_slot'])

            event_id = calendar_service.create_appointment(doctor, patient, appointment_datetime, collected_info.get('duration', 30), collected_info.get('reason', ''))

            new_appointment = {
                "patient_id": patient["id"],
                "doctor_id": doctor["id"],
                "google_calendar_event_id": event_id,
                "scheduled_datetime": appointment_datetime.isoformat(),
                "appointment_type": collected_info.get('appointment_type', 'consultation'),
                "reason": collected_info.get('reason', ''),
                "duration_minutes": collected_info.get('duration', 30),
                "status": "scheduled"
            }

            appointment_response = supabase.table("appointments").insert(new_appointment).execute()
            appointment = appointment_response.data[0]

            await notification_service.send_appointment_confirmation(appointment, patient, doctor)

            ai_agent.clear_context(chat_data.user_id)
            ai_response['appointment_id'] = appointment["id"]
            ai_response['booking_success'] = True

        except Exception as e:
            ai_response['message'] = "I'm sorry, there was an error booking your appointment. Please try again."
            ai_response['booking_success'] = False

    return ai_response

@app.post("/whatsapp")
async def whatsapp_handler(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...)
):
    """
    Handle incoming WhatsApp messages
    Twilio will POST here when user sends a message
    """
    # Extract just the number (remove 'whatsapp:' prefix)
    user_id = From.replace("whatsapp:", "")
    
    # Process message with AI agent
    ai_response = ai_agent.process_message(user_id, Body)

    # Respond via WhatsApp
    response = MessagingResponse()
    msg = response.message(ai_response.get("message", "Sorry, I couldn't understand that."))

    return str(response)

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: int):
    response = supabase.table("appointments").select("*").eq("id", appointment_id).single().execute()
    appointment = response.data
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    patient = supabase.table("patients").select("name").eq("id", appointment["patient_id"]).single().execute().data
    doctor = supabase.table("doctors").select("name").eq("id", appointment["doctor_id"]).single().execute().data
    return {
        "id": appointment["id"],
        "patient_name": patient["name"],
        "doctor_name": doctor["name"],
        "scheduled_datetime": appointment["scheduled_datetime"],
        "status": appointment["status"],
        "reason": appointment["reason"]
    }

@app.post("/api/appointments/{appointment_id}/reschedule")
async def reschedule_appointment(appointment_id: int, new_datetime: datetime):
    response = supabase.table("appointments").select("*").eq("id", appointment_id).single().execute()
    appointment = response.data
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Update in Google Calendar
    # ... (not implemented here)

    # Update in Supabase
    supabase.table("appointments").update({"scheduled_datetime": new_datetime.isoformat()}).eq("id", appointment_id).execute()

    # Send confirmation
    patient = supabase.table("patients").select("*").eq("id", appointment["patient_id"]).single().execute().data
    doctor = supabase.table("doctors").select("*").eq("id", appointment["doctor_id"]).single().execute().data
    await notification_service.send_appointment_confirmation(appointment, patient, doctor)

    return {"message": "Appointment rescheduled successfully"}

@app.get("/auth/google")
async def google_auth():
    auth_url, flow = calendar_service.get_authorization_url()
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def google_callback(code: str):
    # Implement OAuth callback logic
    return {"message": "Authorization successful"}

if __name__ == "__main__":
    import uvicorn
    scheduler = AppointmentScheduler(notification_service)
    scheduler.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)