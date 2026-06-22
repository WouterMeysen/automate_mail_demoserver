# utils/drive_uploader.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = logging.getLogger("drive_uploader")
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.metadata.readonly"]

class DriveUploader:
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._get_creds()
        self.service = build("drive", "v3", credentials=self.creds)

    def _get_creds(self):
        creds = None
        if os.path.exists(self.token_path):
            import json
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Use google.oauth2.credentials.Credentials
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_info(data, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # save token
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        return creds

    def upload_file(self, file_path, file_name, folder_id=None):
        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        media = MediaFileUpload(file_path, mimetype="text/csv")
        file = self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return file.get("id")
