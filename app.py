from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os.path, pickle, base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

app = Flask(__name__, static_folder="static")
CORS(app)

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]
CALENDAR_ID = 'f8a74ebfc91e17b2a29d2717d6f120333a01d74da95ad3b297e870dc3763dcfd@group.calendar.google.com'
AVAILABLE_TIMES = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]

def get_google_service(api_name, api_version):
    """Authenticate once for all Google APIs."""
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.pkl')
    
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(os.path.dirname(__file__), 'credentials.json'),SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)
    return build(api_name, api_version, credentials=creds)

def send_confirmation_email(to_email, name, date, time):
    gmail_service = get_google_service('gmail', 'v1')

    subject = f"Booking Confirmation – Bumblebee Gardening"
    body = f"""
    Hi {name},

    Thank you for booking with Bumblebee Gardening!

    Your appointment is confirmed for:
    📅 {date} at {time}

    We look forward to helping you with your garden 🌿

    — The Bumblebee Gardening Team
    """

    message = MIMEText(body)
    message['to'] = to_email
    message['from'] = "me"
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={'raw': raw_message}).execute()

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/availability/<date>", methods=["GET"])
def availability(date):
    service = get_google_service('calendar', 'v3')
    start_of_day = f"{date}T00:00:00Z"
    end_of_day = f"{date}T23:59:59Z"

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    booked_times = []
    for event in events_result.get('items', []):
        start = event['start']
        
        # Skip all-day events (which use 'date')
        if 'dateTime' in start:
            booked_times.append(start['dateTime'][11:16])
    print("Booked times found:", booked_times)
    free_slots = [t for t in AVAILABLE_TIMES if t not in booked_times]
    return jsonify({"date": date, "available": free_slots})

@app.route("/book", methods=["POST"])
def book():
    data = request.json
    name = data["name"]
    email = data["email"]
    date = data["date"]
    time = data["time"]

    service = get_google_service('calendar', 'v3')
    start_dt = datetime.fromisoformat(f"{date}T{time}:00")
    end_dt = start_dt + timedelta(hours=1)

    start_iso = start_dt.isoformat() + 'Z'
    end_iso = end_dt.isoformat() + 'Z'

    # Check if already booked
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True
    ).execute()
    if events_result.get('items'):
        return jsonify({"status": "error", "message": "This slot is already booked."})

    # Create new event
    event = {
        'summary': f'Booking: {name}',
        'description': f'Client: {name}\nEmail: {email}',
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/London'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/London'}
    }
    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

    # Send email confirmation
    try:
        send_confirmation_email(email, name, date, time)
        return jsonify({"status": "success", "message": f"Booking confirmed and email sent to {email}!"})
    except Exception as e:
        print("Email error:", e)
        return jsonify({"status": "success", "message": "Booking confirmed, but email failed."})

@app.route("/calendar", methods=["GET"])
def calendar_data():
    service = get_google_service('calendar', 'v3')

    today = datetime.today().date()
    events = []
    total_slots = len(AVAILABLE_TIMES)

    # Generate events for the next 30 days
    for i in range(45):
        date = today + timedelta(days=i)

        # Skip weekends (Saturday=5, Sunday=6)
        if date.weekday() >= 5:
            continue

        date_str = date.isoformat()

        start_of_day = datetime.combine(date, datetime.min.time()).isoformat() + "Z"
        end_of_day = datetime.combine(date, datetime.max.time()).isoformat() + "Z"

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        booked = [
            event for event in events_result.get('items', [])
            if event.get('start', {}).get('dateTime')  # Ignore all-day events
        ]
        booked_count = len(booked)

        # Calendar Colors
        if date < today:
            color = "darkgrey"
            title = "Past"
        elif booked_count == 0:
            color = "green"
            title = "Available"
        elif booked_count < total_slots:
            color = "orange"
            title = f"Available ({total_slots-booked_count}/{total_slots})"
        else:
            color = "red"
            title = "Fully Booked"

        events.append({
            "title": title,
            "start": date_str,
            "allDay": True,
            "color": color
        })

    return jsonify(events)


if __name__ == "__main__":
    app.run(debug=True)
