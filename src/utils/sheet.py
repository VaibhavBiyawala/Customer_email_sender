import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def load_google_sheet(sheet_name):
    """Connects to a Google Sheet and returns data as a pandas DataFrame."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('D:\Sem 7\BreakThough_AI\Customer_email_sender\GCloud\email-sender-441304-e637b6539380.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def load_csv(file_path):
    """Loads data from a CSV file and returns it as a pandas DataFrame."""
    return pd.read_csv(file_path)

def get_google_sheets():
    """Returns a list of all Google Sheets in the user's account."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('D:\Sem 7\BreakThough_AI\Customer_email_sender\GCloud\email-sender-441304-e637b6539380.json', scope)
    client = gspread.authorize(creds)
    print("\n Client:", client, "\n")
    # Fetch all spreadsheets
    sheets = client.list_spreadsheet_files()
    print("\n Sheets:", sheets, "\n")
    return [sheet['name'] for sheet in sheets]
