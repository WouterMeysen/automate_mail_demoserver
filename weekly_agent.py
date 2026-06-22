# weekly_agent.py
import os
import sys
import logging
import datetime
import yaml
from utils.email_reader import GmailReader
from utils.body_parser import parse_table_text_to_df
from utils.drive_uploader import DriveUploader
from utils.sheet_appender import SheetAppender

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("weekly_agent")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    cfg_path = os.path.join(BASE_DIR, "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_config()
    today = datetime.date.today()
    date_str = today.isoformat()

    # 1. Read email
    reader = GmailReader(
        imap_host=cfg["email"]["imap_host"],
        imap_port=cfg["email"]["imap_port"],
        username=cfg["email"]["username"],
        app_password=cfg["email"]["app_password"],
    )

    logger.info("Searching for the weekly email")
    raw_body = reader.fetch_latest_email_body(
        from_address=cfg["filter"]["from_address"],
        subject=cfg["filter"]["subject"],
        date=today
    )

    if not raw_body:
        logger.info("No matching email found for today. Exiting.")
        return

    # 2. Parse body into DataFrame
    df = parse_table_text_to_df(raw_body)
    if df.empty:
        logger.warning("Parsed DataFrame is empty. Exiting.")
        return

    # 3. Save weekly CSV locally
    csv_filename = f"{date_str}.csv"
    csv_path = os.path.join(BASE_DIR, csv_filename)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved weekly CSV to {csv_path}")

    # 4. Upload CSV to Drive
    drive_uploader = DriveUploader(credentials_path=os.path.join(BASE_DIR, "credentials.json"),
                                   token_path=os.path.join(BASE_DIR, "token.json"))
    folder_id = cfg["drive"]["drive_folder_id"]
    uploaded_file_id = drive_uploader.upload_file(csv_path, csv_filename, folder_id)
    logger.info(f"Uploaded CSV to Drive with file id {uploaded_file_id}")

    # 5. Append to master Google Sheet
    sheet_appender = SheetAppender(credentials_path=os.path.join(BASE_DIR, "credentials.json"),
                                   token_path=os.path.join(BASE_DIR, "token.json"))
    master_sheet_id = cfg["sheets"]["master_sheet_id"]
    range_name = cfg["sheets"].get("master_sheet_range", "Sheet1!A:C")

    # Optional deduplication: fetch existing emails from sheet and avoid duplicates
    sheet_appender.append_dataframe(master_sheet_id, range_name, df, deduplicate_on="EMAIL")
    logger.info("Appended rows to master Google Sheet")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Unhandled exception in weekly_agent")
        sys.exit(1)
