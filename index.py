import urllib
import json
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
from pymongo import MongoClient
# from flask_dance.contrib.google import make_google_blueprint, google
# from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
import random
from datetime import datetime


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
# jwt = JWTManager(app)
app.secret_key = os.getenv("JWT_SECRET_KEY")  # Required for sessions

# MongoDB configuration
client = MongoClient(os.getenv('MONGODB_URL'))
db = client['AI_Chef_Master']

# Collections
email_collection = db.Email
chef_email_collection = db.ChefEmail

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = os.getenv("SMTP_PORT", 587)
SMTP_EMAIL = str(os.getenv("SMTP_EMAIL"))  # Your email
SMTP_PASSWORD = str(os.getenv("SMTP_PASSWORD"))  # Your email password

# google login
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

# google_blueprint = make_google_blueprint(
#     client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
#     client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
#     scope=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile",
#            "openid"]
# )
#app.register_blueprint(google_blueprint, url_prefix="/login")
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# =======================================================================================================================================

# Function to send email
def send_email(recipient_email, subject, body):
    try:
        # Create email message
        message = MIMEMultipart()
        message["From"] = SMTP_EMAIL
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "html"))

        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, recipient_email, message.as_string())
        print(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def gen_ticket():
    random_string = uuid.uuid4().hex[:45]
    return f"{random_string}"


@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data = request.get_json()
        email = data.get("emails")
        if db.subscribers.count_documents({"email":email})>0:
            return jsonify({"msg":"Subscribed"})
        otp = str(random.randint(111111, 1000000))
        logo_url = "https://www.aichefmaster.com/assets/logo.jpeg"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }}
        .container {{
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .content {{
            padding: 20px;
            font-size: 16px;
            line-height: 1.5;
            color: #333333;
        }}
        .otp {{
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            color: #4CAF50;
        }}
        .footer {{
            background-color: #f4f4f4;
            text-align: center;
            padding: 10px;
            font-size: 12px;
            color: #999999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{logo_url}" alt="AI Chef Master Logo" />
            <h1>Welcome to AI Chef Master!</h1>
        </div>
        <div class="content">
            <p>Hey there!</p>
            <p>Here is your OTP. Please don't share it with anyone:</p>
            <div class="otp">{otp}</div>
        </div>
        <div class="footer">
            <p>Thank you for using our service!</p>
        </div>
    </div>
</body>
</html>
"""
        status = send_email(email, "Welcome to AiChefMaster", html_content)
        ticket = gen_ticket()
        if db.OTPStore.count_documents({"ticket":ticket})>0:
            ticket = gen_ticket()
        db.OTPStore.insert_one({"ticket":ticket, "otp":otp, "time":datetime.utcnow()})
        if status:
            return jsonify({"ticket":f"{ticket}"})
        else:
            return jsonify({"msg":"error"})
    except Exception as e:
        return jsonify({"msg":"e"+str(e)}), 500

@app.route("/validate-otp", methods=["POST"])
def validate():
    data = request.get_json()
    try:
        otp = db.OTPStore.find_one({"ticket":data.get("tickets")})
        if otp['otp'] == data.get("otps"):
            db.OTPStore.delete_one({"ticket":data.get("tickets")})
            db.subscribers.insert_one({"email":data.get("emails"),"createdAt":datetime.utcnow(), "features":""})
            return jsonify({"msg":"v"}), 200
        else:
            return jsonify({"msg":"n"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}), 422

@app.route("/submit-feed", methods=['POST'])
def submitFeed():
    data = request.get_json()
    try:
        features = data.get("features")
        if len(features) == 4:
            features = "All"
        email = data.get("emails")
        entered = db.subscribers.update_one({"email":email}, {"$set":{"features":features}})
        # Attach the email body
        logo_url = "https://www.aichefmaster.com/assets/logo.jpeg"  # Replace with your logo URL
        social_media_html = f"""
    <a href="https://twitter.com/AI_Chef_Master" target="_blank">
        <img style="height: 10px" src="https://upload.wikimedia.org/wikipedia/commons/6/60/Twitter_Logo_2021.svg" alt="Twitter" style="width: 30px; margin: 0 10px;"/>
    </a>
    <a href="https://facebook.com/AI_Chef_Master" target="_blank">
        <img style="height: 10px" src="https://upload.wikimedia.org/wikipedia/commons/5/51/Facebook_f_logo_%282019%29.svg" alt="Facebook" style="width: 30px; margin: 0 10px;"/>
    </a>
    <a href="https://linkedin.com/company/AI_Chef_Master" target="_blank">
        <img style="height: 10px" src="https://upload.wikimedia.org/wikipedia/commons/0/01/LinkedIn_Logo_2023.svg" alt="LinkedIn" style="width: 30px; margin: 0 10px;"/>
    </a>
    <a href="https://instagram.com/AI_Chef_Master" target="_blank">
        <img style="height: 10px" src="https://upload.wikimedia.org/wikipedia/commons/9/95/Instagram_logo_2022.svg" alt="Instagram" style="width: 30px; margin: 0 10px;"/>
    </a>
"""
        body = f"""<html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f9f9f9;">

        <div style="background-color: #1f2937; padding: 20px; text-align: center;">
            <img src="{logo_url}" alt="Company Logo" style="max-width: 150px; margin-bottom: 10px; border-radius: 9999px;" />
            <h1 style="color: #ffffff; margin: 0;">Welcome to AI Chef Master</h1>
        </div>

        <div style="padding: 20px; background-color: #ffffff; margin: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
            <p>Hi <strong>{email}</strong>,</p>
            <p>We’re thrilled to have you on board. Your first step towards AI Chef Master.</p>
            <p>
                We started AI Chef Master to address common challenges in cooking, such as time constraints, lack of personalisation, 
                and inefficient ingredient management. Our motivation stems from a passion for culinary innovation and a desire to make 
                cooking more accessible, enjoyable, and efficient for everyone.
            </p>
            <p>
                By leveraging AI technology, we aim to empower home cooks with personalised recipes, regional language support, 
                and step-by-step guidance, revolutionising the cooking experience and helping individuals create delicious meals with ease.
            </p>

            <!-- Free Subscription Section -->
            <p style="font-size: 16px; color: #333; font-weight: bold; margin-top: 20px;">
                🎉 Good News! You've received a <strong>1-Year Free Subscription</strong> to AI Chef Master! 🎉
            </p>
            <p style="font-size: 14px; color: #666; margin-top: 10px;">
                Explore exclusive features and personalised AI-powered culinary tools to make your cooking journey easier and more delightful. 
                This is our way of saying thank you for joining us!
            </p>

            <p>If you have any queries, please contact us at <a href="mailto:support.acm@aichefmaster.com" style="color: #1a73e8;">support.acm@aichefmaster.com</a>. We will get back to you as soon as possible.</p>
            <p>Thank you!</p>
            <p>Best regards,<br><strong>AI Chef Master</strong></p>
            <strong>info.ai@aichefmaster.com</strong>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 20px; background-color: #f4f4f4; font-size: 14px; color: #666;">
            <div style="margin-bottom: 10px;height: "20px">{social_media_html}</div>
            <p style="margin: 0;">&copy; AI Chef Master, 2023. All rights reserved.</p>
        </div>
    </body>
</html>
"""
        sent = send_email(email, "Welcome to AI Chef Master", body)
        if entered:
            return jsonify({"msg":"All set"}), 200
        else:
            return jsonify({"msg":"Internal error occured!"}), 500
    except Exception as e:
        return jsonify({"error":str(e)}), 422
if __name__ == '__main__':
    app.debug = True
    app.run()
