from flask import Flask, request, jsonify
import os
import sqlite3
from groq import Groq
from dotenv import load_dotenv
import logging
from postmark import send_email  # Import the function from postmark.py

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
POSTMARK_API_KEY = os.getenv("POSTMARK_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # Your verified email in Postmark
if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")
if not POSTMARK_API_KEY:
    raise ValueError("POSTMARK_API_KEY not found in environment variables")
if not SENDER_EMAIL:
    raise ValueError("SENDER_EMAIL not found in environment variables")

groq_client = Groq(api_key=API_KEY)

# Store user's email ID for sending later
user_email = None

# Hotel information constant
HOTEL_INFO = """Thira Beach Home is a luxurious seaside retreat that seamlessly blends Italian-Kerala heritage architecture with modern luxury, creating an unforgettable experience. Nestled just 150 meters from the magnificent Arabian Sea, our beachfront property offers a secluded and serene escape with breathtaking 180-degree ocean views. 

The accommodations feature Kerala-styled heat-resistant tiled roofs, natural stone floors, and lime-plastered walls, ensuring a perfect harmony of comfort and elegance. Each of our Luxury Ocean View Rooms is designed to provide an exceptional stay, featuring a spacious 6x6.5 ft cot with a 10-inch branded mattress encased in a bamboo-knitted outer layer for supreme comfort.

Our facilities include:
- Personalized climate control with air conditioning and ceiling fans
- Wardrobe and wall mirror
- Table with attached drawer and two chairs
- Additional window bay bed for relaxation
- 43-inch 4K television
- Luxury bathroom with body jets, glass roof, and oval-shaped bathtub
- Total room area of 250 sq. ft.

Modern amenities:
- RO and UV-filtered drinking water
- 24/7 hot water
- Water processing unit with softened water
- Uninterrupted power backup
- High-speed internet with WiFi
- Security with CCTV surveillance
- Electric charging facility
- Accessible design for differently-abled persons

Additional services:
- Yoga classes
- Cycling opportunities
- On-site dining at Samudrakani Kitchen
- Stylish lounge and dining area
- Long veranda with ocean views

Location: Kothakulam Beach, Valappad, Thrissur, Kerala
Contact: +91-94470 44788
Email: thirabeachhomestay@gmail.com"""


# Connect to SQLite database
def connect_to_db():
    return sqlite3.connect('rooms.db')

# Fetch room details from the database
def fetch_room_details():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute('SELECT title, description FROM room_data')
    results = cursor.fetchall()
    conn.close()
    if results:
        return "\n\n".join([f"Room: {title}\nDescription: {desc}" for title, desc in results])
    return "No room details available."

# Classify the query
def classify_query(query):
    prompt = f"""Classify the following query:
    1. Checking details - if it's about booking a hotel room
    2. Getting information - if it's about general hotel info.
    
    Query: {query}
    Respond with only the number (1 or 2)."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10
    )
    return response.choices[0].message.content.strip()

# Generate response
def generate_response(query, context):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are Maya, a friendly hotel receptionist."},
            {"role": "user", "content": f"Query: {query}\nContext: {context}"}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

@app.route('/query', methods=['POST'])
def handle_query():
    global user_email  # Store user's email

    data = request.get_json()
    query = data.get("query", "")
    email_id = data.get("email", None)  # Capture email if provided

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    query_type = classify_query(query)

    if query_type == "1":  # Booking inquiry
        if not email_id:
            return jsonify({"response": "Please provide your email ID to receive room details."})

        user_email = email_id  # Store email
        room_details = fetch_room_details()
        send_email(user_email, "Room Availability at Thira Beach Home", room_details)
        return jsonify({"response": f"Room details have been sent to {user_email}."})
    
    elif query_type == "2":  # General inquiry
        return jsonify({"response": "Thira Beach Home offers luxurious stays with modern amenities."})

    elif query_type == "3":  # User provides email
        return jsonify({"response": f"Thank you! We'll send details to {query} shortly."})

    else:
        return jsonify({"response": "Sorry, I couldn't understand your request."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
