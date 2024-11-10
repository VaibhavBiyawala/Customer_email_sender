# Custom Email Sender

This project is a custom email sender application that allows users to upload data, customize email prompts, and send bulk emails with real-time analytics. The application supports both CSV file uploads and Google Sheets integration.

## Features

- Upload data from CSV files or Google Sheets
- Customize email prompts using a template
- Send bulk emails using the Mailgun API
- Schedule emails to be sent at a specific time
- Real-time email status dashboard
- Real-time email analytics

## Prerequisites

- Python 3.7+
- Redis (for Celery)
- Ngrok (for webhook URL)
- Mailgun account and API key
- Google Cloud service account credentials for Google Sheets access

## Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/custom-email-sender.git
    cd custom-email-sender
    ```

2. Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables:

    Create a `.env` file in the root directory and add the following variables:

    ```env
    MAILGUN_API_KEY=your_mailgun_api_key
    MAILGUN_DOMAIN=your_mailgun_domain
    MAILGUN_SIGNING_KEY=your_mailgun_signing_key
    GROQ_API_KEY=your_groq_api_key
    ```

5. Set up Google Cloud service account credentials:

    Place your Google Cloud service account JSON file in the `GCloud` directory and update the file path in `src/utils/sheet.py` and `src/utils/mailgun.py`.

6. Start Redis server:

    ```bash
    redis-server
    ```

7. Start Ngrok to expose the local server:

    ```bash
    ngrok http 5000
    ```

8. Run the Flask application:

    ```bash
    python src/app.py
    ```

## Usage

1. Open the application in your browser:

    ```bash
    http://localhost:5000
    ```

2. Upload data:

    - Navigate to the "Upload Data" page.
    - Select the input type (CSV File or Google Sheet).
    - Upload the file or select the Google Sheet.
    - Click "Upload".

3. Customize and send emails:

    - Navigate to the "Send Emails" page.
    - Customize the email prompt using the provided template.
    - Select the column for email addresses.
    - Schedule the emails or send them immediately.
    - Click "Send Emails".

4. View real-time analytics:

    - Navigate to the "Real-Time Analytics" page to view email metrics.
    - Navigate to the "Email Status Dashboard" page to view the status of individual emails.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.