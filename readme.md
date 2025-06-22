#.env Format
SUPABASE_URL=""
SUPABASE_KEY=""
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GOOGLE_REDIRECT_URI=""
GROQ_API_KEY=""
TWILIO_ACCOUNT_SID=""
TWILIO_AUTH_TOKEN=""
TWILIO_WHATSAPP_NUMBER=""
REDIS_URL="redis://localhost:6379"
#clone the github project
<pre>
git clone https://github.com/Godzilaa/whatsapp_bot/edit/main/readme.md
</pre>
#change the directory
<pre>
cd whatsapp_bot
</pre>
#install the requirements
<pre>
pip install uvicorn
pip install -r requirements.txt
</pre>
#Run the main file
<pre>
uvicorn main:app
</pre>
