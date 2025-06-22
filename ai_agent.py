# ai_agent.py

import json
import re
from datetime import datetime, timedelta
from groq import Groq
from config import Config
from fastapi import Form

class AIAppointmentAgent:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.conversation_context = {}

    def process_message(self, user_id, message, available_doctors=None):
        """Process user message and return appropriate response"""
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = {
                'stage': 'greeting',
                'collected_info': {}
            }
        context = self.conversation_context[user_id]

        system_prompt = f"""You are a helpful AI assistant for a medical clinic. Your job is to help patients book appointments.
Available doctors and their specialties:
{json.dumps([{'name': d.name, 'specialty': d.specialty} for d in available_doctors]) if available_doctors else "[]"}
Conversation stages:
1. greeting - Welcome and understand what they need
2. doctor_selection - Help them choose appropriate doctor
3. info_collection - Collect patient information (name, email, phone, reason)
4. scheduling - Show available slots and book appointment
5. confirmation - Confirm details and provide next steps
Current stage: {context['stage']}
Collected info: {json.dumps(context['collected_info'])}
Guidelines:
- Be friendly and professional
- Ask for one piece of information at a time
- Validate email and phone formats
- Suggest appointment slots clearly
- Always confirm details before booking
Respond in JSON format:
{{
    "message": "Your response to the patient",
    "next_stage": "next_conversation_stage",
    "extracted_info": {{"key": "value"}},
    "action_needed": "book_appointment|get_availability|none"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            ai_response = json.loads(response.choices[0].message.content)
            context['stage'] = ai_response.get('next_stage', context['stage'])
            context['collected_info'].update(ai_response.get('extracted_info', {}))
            return ai_response
        except Exception as e:
            return {
                "message": "I apologize, but I'm having trouble processing your request. Could you please try again?",
                "next_stage": context['stage'],
                "extracted_info": {},
                "action_needed": "none"
            }

    def clear_context(self, user_id):
        if user_id in self.conversation_context:
            del self.conversation_context[user_id]