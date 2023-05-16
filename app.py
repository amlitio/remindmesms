from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client

app = Flask(__name__)

# Configure the SQLAlchemy part of the app instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reminders.db'

# Create the SQLAlchemy db instance
db = SQLAlchemy(app)

# Twilio account information
account_sid = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
auth_token = "your_auth_token"

# Create a Twilio client
client = Client(account_sid, auth_token)

# Create a reminder model
class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255))
    time = db.Column(db.DateTime)
    timezone = db.Column(db.String(255))

# Create a reminder table
db.create_all()

@app.route("/")
def index():
    # Get all reminders
    reminders = Reminder.query.all()

    return render_template("index.html", reminders=reminders)

@app.route("/add", methods=["POST"])
def add():
    # Get the reminder text and time from the request
    text = request.form["text"]
    time = request.form["time"]
    timezone = request.form["timezone"]

    # Create a new reminder
    reminder = Reminder(text=text, time=time, timezone=timezone)

    # Save the reminder to the database
    db.session.add(reminder)
    db.session.commit()

    # Schedule a task to send the message at the right time
    from celery import Celery
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'
    celery = Celery(app)

    @celery.task
    def send_reminder(reminder):
        client.messages.create(
            to=reminder.phone_number,
            from_="+15555555555",
            body=reminder.text
        )

    celery.send_reminder.delay(reminder)

    return redirect("/")

if __name__ == "__main__":
    app.run()
