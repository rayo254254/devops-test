# gdrive_oauth_uploader.py
import os
from io import BytesIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def authenticate_drive():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def upload_doc_from_memory(file_content, filename, mime_type, folder_id):
    service = authenticate_drive()
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(BytesIO(file_content), mimetype=mime_type, resumable=True)
    uploaded_file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )
    print(f"✅ Uploaded '{uploaded_file['name']}' → {uploaded_file['webViewLink']}")
    return uploaded_file
