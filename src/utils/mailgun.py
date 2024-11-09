import requests
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')

email_status_metrics = {
    "total_sent": 0,
    "pending": 0,
    "scheduled": 0,
    "failed": 0,
    "delivered": 0,
    "opened": 0,
    "bounced": 0,
    "response_rate": 0.0
}

def update_email_status_metrics(status_code, email_status=None):
    """Updates email status metrics based on the response status code and email status."""
    if email_status == "scheduled":
        email_status_metrics["scheduled"] += 1
    elif email_status == "pending":
        email_status_metrics["pending"] += 1
    elif email_status == "delivered":
        email_status_metrics["delivered"] += 1
    elif email_status == "opened":
        email_status_metrics["opened"] += 1
    elif email_status == "bounced":
        email_status_metrics["bounced"] += 1
    elif email_status == "failed":
        email_status_metrics["failed"] += 1
    elif status_code == 200:
        email_status_metrics["total_sent"] += 1
        if email_status_metrics["pending"] > 0:
            email_status_metrics["pending"] -= 1
    else:
        email_status_metrics["failed"] += 1
        if email_status_metrics["pending"] > 0:
            email_status_metrics["pending"] -= 1

def send_email_via_mailgun(to_email, content, subject="Custom Email"):
    """Sends an email using the Mailgun API."""
    response = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Excited User <mailgun@{MAILGUN_DOMAIN}>",
            "to": [to_email],
            "subject": subject,
            "text": content,
            "o:tracking": "yes",  # Enable tracking
            "o:tracking-opens": "yes"  # Enable open tracking
        }
    )
    
    print("Debug:", response.status_code)
    return response.status_code, response.json()

def get_ngrok_url():
    """Fetch the current ngrok URL."""
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels')
        response.raise_for_status()
        tunnels = response.json().get('tunnels', [])
        if tunnels:
            return tunnels[0].get('public_url')
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch ngrok URL: {e}")
    return None

def update_mailgun_webhook():
    """Update the Mailgun webhook URL with the current ngrok URL."""
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        webhook_url = f"{ngrok_url}/webhook/mailgun"
        try:
            for event in ["delivered", "opened", "bounced", "failed"]:
                response = requests.put(
                    f"https://api.mailgun.net/v3/domains/{MAILGUN_DOMAIN}/webhooks/{event}",
                    auth=("api", MAILGUN_API_KEY),
                    data={"url": webhook_url}
                )
                response.raise_for_status()
            logging.info("Webhook updated successfully.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to update webhook: {e}")
    else:
        logging.error("Ngrok URL is not available.")
