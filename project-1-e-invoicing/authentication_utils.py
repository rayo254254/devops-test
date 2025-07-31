#********************************************************
# TO DO:
# 1. Add function to authenticate with Google Drive using service account (already done in the code below + Carbone flow already has it implemented)
#*********************************************************
from pathlib import Path
import time
import json
import os
#for the filesaves to Google drive
from io import BytesIO
#import os
from google.oauth2.credentials import Credentials

from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
#from google.cloud import secretmanager


#*******************************************************
# Use full drive scope for uploading files
# TO BE USED FOR GCR
SCOPES = ['https://www.googleapis.com/auth/drive']

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = 'service-account.json'

# Step 1: Authenticate using service account
def authenticate_drive_new():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)

# Step 2: Upload doc from memory to specific folder
def upload_doc_from_memory(file_content, filename, mime_type, folder_id):
    drive_service = authenticate_drive_new()
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    buffer = BytesIO(file_content)
    media = MediaIoBaseUpload(buffer, mimetype=mime_type, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name',
        supportsAllDrives=True  # Important for Shared Drives!
    ).execute()
    print(f"✅ Uploaded '{uploaded_file.get('name')}' to Google folder. File ID: {uploaded_file.get('id')}")

#*******************************************************

TOKEN_FILE = Path("token_cache.json")
#******************************************
# Step 1: Authenticate with Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

#******************************************************
# Step 2: Upload XML from memory to specific folder
def upload_xml_memory(service, filename, xml_string, folder_id):
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    buffer = BytesIO(xml_string.encode('utf-8'))
    media = MediaIoBaseUpload(buffer, mimetype='application/xml')
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
    print(f"✅ Uploaded '{filename}' to folder. File ID: {uploaded_file['id']}")

#*****************************************************
def save_token(access_token, expires_in_seconds):
    data = {
        "access_token": access_token,
        "expires_at": time.time() + expires_in_seconds - 30  # subtract buffer
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_token():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        if data.get("expires_at", 0) > time.time():
            return data["access_token"]
    return None
#*****************************************************
"""def get_secret(secret_id, project_id):
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Return the decoded payload.
    return response.payload.data.decode("UTF-8")"""
#*****************************************************