import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def load_google_sheet(sheet_name):
    """Connects to a Google Sheet and returns data as a pandas DataFrame."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def load_csv(file_path):
    """Loads data from a CSV file and returns it as a pandas DataFrame."""
    return pd.read_csv(file_path)
