# utils/email_reader.py
import imaplib
import email
from email.header import decode_header
import datetime
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger("email_reader")

class GmailReader:
    def __init__(self, imap_host, imap_port, username, app_password):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.app_password = app_password

    def _connect(self):
        mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        mail.login(self.username, self.app_password)
        mail.select("inbox")
        return mail

    def _decode_bytes(self, b):
        try:
            return b.decode("utf-8")
        except:
            try:
                return b.decode("latin-1")
            except:
                return str(b)

    def fetch_latest_email_body(self, from_address, subject, date: datetime.date):
        """
        Search for email by FROM, SUBJECT, and date. Return plain text body (or HTML stripped).
        """
        mail = self._connect()
        # IMAP date format: 22-Jun-2026
        imap_date = date.strftime("%d-%b-%Y")
        # Build search criteria
        # Use SUBJECT and FROM and SINCE to narrow down
        criteria = f'(FROM "{from_address}" SUBJECT "{subject}" SINCE {imap_date})'
        logger.debug("IMAP search criteria: %s", criteria)
        result, data = mail.search(None, criteria)
        if result != "OK":
            logger.error("IMAP search failed: %s", result)
            return None

        ids = data[0].split()
        if not ids:
            logger.info("No messages found")
            return None

        # take the latest message id
        latest_id = ids[-1]
        res, msg_data = mail.fetch(latest_id, "(RFC822)")
        if res != "OK":
            logger.error("Failed to fetch message")
            return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Walk parts to find text/plain or text/html
        body_text = None
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    body_text = part.get_payload(decode=True)
                    break
            if body_text is None:
                # fallback to html
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/html":
                        html = part.get_payload(decode=True)
                        body_text = self._html_to_text(html)
                        break
        else:
            ctype = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if ctype == "text/plain":
                body_text = payload
            elif ctype == "text/html":
                body_text = self._html_to_text(payload)

        if body_text is None:
            logger.warning("No body found in message")
            return None

        if isinstance(body_text, bytes):
            body_text = self._decode_bytes(body_text)

        # Clean up common email quoting lines
        body_text = self._clean_body_text(body_text)
        mail.logout()
        return body_text

    def _html_to_text(self, html_bytes):
        try:
            html = html_bytes.decode("utf-8", errors="ignore")
        except:
            html = str(html_bytes)
        soup = BeautifulSoup(html, "lxml")
        # remove scripts/styles
        for s in soup(["script", "style"]):
            s.decompose()
        text = soup.get_text(separator="\n")
        return text

    def _clean_body_text(self, text):
        # Remove repeated blank lines and trim
        lines = [line.rstrip() for line in text.splitlines()]
        # Remove email reply separators and lines starting with >
        cleaned = []
        for line in lines:
            if line.strip().startswith(">"):
                continue
            if line.strip().lower().startswith("from:") or line.strip().lower().startswith("sent:"):
                continue
            cleaned.append(line)
        # Remove leading/trailing empty lines
        while cleaned and cleaned[0].strip() == "":
            cleaned.pop(0)
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        return "\n".join(cleaned)
