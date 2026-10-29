import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()


def send_email(receiver_email, subject, message):

    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    email = EmailMessage()

    email["From"] = sender_email
    email["To"] = receiver_email
    email["Subject"] = subject

    email.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

        server.login(sender_email, app_password)

        server.send_message(email)