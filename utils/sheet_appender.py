# utils/sheet_appender.py
import os
import logging
import json
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger("sheet_appender")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class SheetAppender:
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._get_creds()
        self.service = build("sheets", "v4", credentials=self.creds)

    def _get_creds(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            creds = Credentials.from_authorized_user_info(data, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        return creds

    def _get_existing_emails(self, spreadsheet_id, range_name):
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get("values", [])
        if not values:
            return set()
        # assume header in first row
        df = pd.DataFrame(values[1:], columns=values[0])
        if "EMAIL" in df.columns:
            return set(df["EMAIL"].astype(str).str.strip().tolist())
        return set()

    def append_dataframe(self, spreadsheet_id, range_name, df, deduplicate_on=None):
        """
        Append DataFrame rows to sheet. If deduplicate_on provided, fetch existing values and skip duplicates.
        """
        sheet = self.service.spreadsheets()
        # deduplicate
        if deduplicate_on:
            existing = self._get_existing_emails(spreadsheet_id, range_name)
            df = df[~df[deduplicate_on].astype(str).str.strip().isin(existing)]
            if df.empty:
                logger.info("No new rows to append after deduplication")
                return

        # Prepare values (no header)
        values = df.fillna("").values.tolist()
        body = {"values": values}
        result = sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        logger.info("Appended %s rows to sheet", result.get("updates", {}).get("updatedRows", 0))
        return result
