# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Supabase replaces your PostgreSQL database and some auth functionality
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # You might still want to keep Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    
    # AI services
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Communication services (Supabase has email/SMS but you might keep these)
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")  # Only if not using Supabase SMS
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    
    # Redis (if not using Supabase Realtime)
    REDIS_URL = os.getenv("REDIS_URL")