from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import pandas as pd
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from utils.mailgun import send_email_via_mailgun, update_email_status_metrics, email_status_metrics, update_mailgun_webhook
from utils.llm import generate_email_content
from utils.sheet import load_google_sheet, load_csv, get_google_sheets
from celery import Celery
import os
import time
import logging
from flask_socketio import SocketIO, emit
import hashlib
import hmac
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Background scheduler for handling scheduled emails
scheduler = BackgroundScheduler()
scheduler.start()

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

email_status_details = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    input_type = request.form.get('input_type')
    if input_type == 'google_sheet':
        sheet_name = request.form.get('sheet_name')
        data = load_google_sheet(sheet_name)
        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        # Save the uploaded file to the uploads directory
        file_path = os.path.join('uploads', sheet_name + '.csv')
        data.to_csv(file_path, index=False)
        print(f"File saved to {file_path}")

         # Verify the file content
        try:
            if file_path.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                data = pd.read_excel(file_path)
            print(f"Data loaded: {data.head()}")
        except pd.errors.EmptyDataError:
            return "No columns to parse from file.", 400
        except pd.errors.ParserError as e:
            return f"Error parsing file: {e}", 400
    else:
        file = request.files['file']
        if file:
            # Ensure the uploads directory exists
            if not os.path.exists('uploads'):
                os.makedirs('uploads')

            # Save the uploaded file to the uploads directory
            file_path = os.path.join('uploads', file.filename)
            file.save(file_path)
            print(f"File saved to {file_path}")

            # Verify the file content
            try:
                if file.filename.endswith('.csv'):
                    data = pd.read_csv(file_path)
                elif file.filename.endswith('.xlsx'):
                    data = pd.read_excel(file_path)
                print(f"Data loaded: {data.head()}")
            except pd.errors.EmptyDataError:
                return "No columns to parse from file.", 400
            except pd.errors.ParserError as e:
                return f"Error parsing file: {e}", 400

    # Extract columns and prepare for further use
    columns = data.columns.tolist()
    return render_template('index.html', columns=columns, file_path=file_path)

@app.route('/list-sheets', methods=['GET'])
def list_sheets():
    sheets = get_google_sheets()
    return jsonify(sheets)

@app.route('/send-email', methods=['POST'])
def send_email():
    # Extract email customization data from the request
    prompt_template = request.form['prompt']
    data_file_path = request.form['file_path']
    email_col = request.form['email_column']
    schedule_time = request.form.get('schedule_time')
    batch_size = int(request.form.get('batch_size', 0))
    interval = int(request.form.get('interval', 0))
    rate_limit = int(request.form.get('rate_limit', 0))

    if schedule_time:
        schedule_time = datetime.strptime(schedule_time, '%Y-%m-%dT%H:%M')
    else:
        schedule_time = datetime.now()

    if os.stat(data_file_path).st_size == 0:
        return "The uploaded file is empty.", 400

    # Try reading the CSV file with different encodings
    try:
        data = pd.read_csv(data_file_path, encoding='utf-8')
    except UnicodeDecodeError:
        data = pd.read_csv(data_file_path, encoding='latin1')
    except pd.errors.EmptyDataError:
        return "No columns to parse from file.", 400
    except pd.errors.ParserError as e:
        return f"Error parsing CSV file: {e}", 400

    if batch_size > 0 and interval > 0:
        for i in range(0, len(data), batch_size):
            batch = data.iloc[i:i + batch_size]
            scheduler.add_job(send_batch_emails, 'date', run_date=schedule_time, args=[batch, prompt_template, email_col, rate_limit])
            update_email_status_metrics(None, "scheduled")
            email_status_metrics["pending"] += len(batch)
            schedule_time += timedelta(minutes=interval)
    else:
        email_status_metrics["pending"] += len(data)
        send_batch_emails.delay(data, prompt_template, email_col, rate_limit)

    return render_template('index.html', columns=data.columns.tolist(), file_path=data_file_path)

@app.route('/analytics')
def analytics():
    return jsonify(email_status_metrics)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/email-status')
def email_status():
    return jsonify(email_status_details)

def verify_mailgun_signature(token, timestamp, signature):
    """Verifies the Mailgun webhook signature."""
    signing_key = os.getenv('MAILGUN_SIGNING_KEY')
    if abs(time.time() - int(timestamp)) > 15:
        return False
    expected_signature = hmac.new(
        key=signing_key.encode('utf-8'),
        msg=f'{timestamp}{token}'.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

@app.route('/webhook/mailgun', methods=['POST'])
def mailgun_webhook():
    print("Webhook received")
    logging.debug("Webhook received")
    
    if request.content_type == 'application/x-www-form-urlencoded':
        token = request.form.get('token')
        timestamp = request.form.get('timestamp')
        signature = request.form.get('signature')
        event_data = request.form.to_dict()
    elif request.content_type == 'application/json':
        data = request.get_json()
        token = data.get('signature', {}).get('token')
        timestamp = data.get('signature', {}).get('timestamp')
        signature = data.get('signature', {}).get('signature')
        event_data = data
    else:
        logging.warning("Unsupported content type.")
        return '', 400

    logging.debug(f"Webhook received: token={token}, timestamp={timestamp}, signature={signature}")
    logging.debug(f"Event data: {json.dumps(event_data, indent=2)}")

    if not token or not timestamp or not signature:
        logging.warning("Missing token, timestamp, or signature in the webhook request.")
        return '', 400

    try:
        timestamp = int(timestamp)
    except ValueError:
        logging.warning("Invalid timestamp value.")
        return '', 400

    if not verify_mailgun_signature(token, timestamp, signature):
        logging.warning("Invalid Mailgun signature.")
        return '', 400

    logging.debug(f"Verified event: {json.dumps(event_data, indent=2)}")
    
    # Extract event type and recipient
    event_type = event_data.get('event-data', {}).get('event')
    recipient = event_data.get('event-data', {}).get('recipient')
    
    # Log the extracted values
    logging.debug(f"Extracted event type: {event_type}, recipient: {recipient}")
    
    if not event_type or not recipient:
        logging.warning("Missing event type or recipient in the webhook data.")
        return '', 400

    logging.debug(f"Event type: {event_type}, Recipient: {recipient}")
    
    for email_status in email_status_details:
        if email_status['email'] == recipient:
            logging.debug(f"Updating status for recipient: {recipient}")
            if event_type == 'delivered':
                email_status["delivery_status"] = "Delivered"
                update_email_status_metrics(None, "delivered")
            elif event_type == 'opened':
                email_status["opened"] = True
                update_email_status_metrics(None, "opened")
            elif event_type == 'bounced':
                email_status["delivery_status"] = "Bounced"
                update_email_status_metrics(None, "bounced")
            elif event_type == 'failed':
                email_status["delivery_status"] = "Failed"
                update_email_status_metrics(None, "failed")
            break
    
    logging.debug(f"Updated metrics: {email_status_metrics}")
    socketio.emit('update_status', email_status_details)
    return '', 200

# Flag to ensure the webhook is updated only once
webhook_updated = True

@app.before_request
def initialize():
    global webhook_updated
    if not webhook_updated:
        update_mailgun_webhook()
        webhook_updated = True

@celery.task
def send_batch_emails(batch, prompt_template, email_col, rate_limit):
    for _, row in batch.iterrows():
        try:
            row_data = {col: str(value) for col, value in row.items()}
            filled_prompt = prompt_template.format(**row_data)
            content = generate_email_content(filled_prompt, row_data)
            email = row[email_col]
            email_status_details.append({
                "company_name": row_data.get("Company Name", "N/A"),
                "email": email,
                "send_status": "Sent",
                "delivery_status": "N/A",
                "opened": False
            })
            status_code, response = send_email_via_mailgun(email, content)
            update_email_status_metrics(status_code, None)
            print(f"Email to {email}: Status {status_code}, Response {response}")
            if rate_limit > 0:
                time.sleep(60 / rate_limit)  # Throttle emails per minute
        except Exception as e:
            email_status_metrics["failed"] += 1
            email_status_metrics["pending"] -= 1
            email_status_details.append({
                "company_name": row_data.get("Company Name", "N/A"),
                "email": email,
                "send_status": "Failed",
                "delivery_status": "Failed",
                "opened": False
            })
            print(f"Error processing row {row}: {e}")

if __name__ == "__main__":
    update_mailgun_webhook()  # Update the webhook URL when the application starts
    socketio.run(app, debug=True)  # Run Flask with SocketIO
