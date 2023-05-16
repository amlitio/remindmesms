from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client
from celery import Celery
from datetime import datetime

app = Flask(__name__)

# Configure the SQLAlchemy part of the app instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reminders.db'

# Create the SQLAlchemy db instance
db = SQLAlchemy(app)

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'
celery = Celery(app)

# Twilio account information
account_sid = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
auth_token = "your_auth_token"

# Create a Twilio client
client = Client(account_sid, auth_token)

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(255), nullable=False)

# Create a reminder table
db.create_all()

@app.route("/")
def index():
    reminders = Reminder.query.all()
    return render_template("index.html", reminders=reminders)

@app.route("/add", methods=["POST"])
def add():
    text = request.form.get("text", "")
    time = request.form.get("time", "")
    timezone = request.form.get("timezone", "")

    # Input validation
    if not text or not time or not timezone:
        flash("Invalid input. Please ensure all fields are filled.")
        return redirect("/")
    
    try:
        time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")  # format of time input
    except ValueError:
        flash("Invalid time format. Please use YYYY-MM-DD HH:MM:SS.")
        return redirect("/")

    reminder = Reminder(text=text, time=time, timezone=timezone)
    db.session.add(reminder)
    db.session.commit()

    send_reminder.apply_async(args=[reminder.id], eta=reminder.time)

    return redirect("/")

@app.route("/delete/<int:reminder_id>", methods=["POST"])
def delete(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    db.session.delete(reminder)
    db.session.commit()
    return redirect("/")

@app.route("/edit/<int:reminder_id>", methods=["POST"])
def edit(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.text = request.form.get("text", reminder.text)
    reminder.timezone = request.form.get("timezone", reminder.timezone)
    try:
        reminder.time = datetime.strptime(request.form.get("time"), "%Y-%m-%d %H:%M:%S")  # format of time input
    except ValueError:
        flash("Invalid time format. Please use YYYY-MM-DD HH:MM:SS.")
        return redirect("/")
    db.session.commit()
    return redirect("/")

@celery.task
def send_reminder(reminder_id):
    reminder = Reminder.query.get(reminder_id)
    client.messages.create(
        to="+15555555555",  # This should be user's phone number
        from_="+15555555555",
        body=reminder.text
    )

if __name__ == "__main__":
    app.run()
