# Demo Server Notifications Automation

This project downloads a weekly email (Monday 10:00) with subject:
**cBioDemoSever Users Report — New Entries**
from sender **henk-jan@thehyve.nl**, parses the table in the email body, saves a weekly CSV, uploads it to Google Drive, and appends rows to a master Google Sheet.

## Prerequisites

1. Python 3.10 or newer
2. VS Code
3. A Google account with Drive and Sheets access
4. Gmail account with App Password enabled (if using 2FA)

## Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
pip install -r requirements.txt
