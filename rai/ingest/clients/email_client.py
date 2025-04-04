import email
from datetime import datetime

from F import LIST


import smtplib
import imaplib
from email.mime.text import MIMEText
from typing import Optional, List

from pydantic import BaseModel


from rai.agentic.ai_modules.log import mLog
from rai.internal.authority import AUTHORITY


class cEmail(mLog):
    class EmailMessage(BaseModel):
        sender: str
        recipients: List[str]
        subject: str
        body: str
        date: datetime

    smtp_client: Optional[smtplib.SMTP] = None
    imap_client: Optional[imaplib.IMAP4_SSL] = None

    sender_email: str = AUTHORITY.get_env("EMAIL_ADDRESS", "charleskromeo@gmail.com")
    app_password: str = AUTHORITY.get_env("EMAIL_PASSWORD", "cjgz bqwz xbzk gpzf")
    smtp_server: str = AUTHORITY.get_env("SMTP_SERVER", "smtp.gmail.com")
    imap_server: str = AUTHORITY.get_env("IMAP_SERVER", "imap.gmail.com")
    smtp_port: int = int(AUTHORITY.get_env("SMTP_PORT", 587))

    def connect(self):
        """Connect once to SMTP and IMAP servers."""
        try:
            if not self.smtp_client:
                self.smtp_client = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                self.smtp_client.starttls()
                self.smtp_client.login(self.sender_email, self.app_password)
                self.log("SMTP connection established and logged in.")

            if not self.imap_client:
                self.imap_client = imaplib.IMAP4_SSL(self.imap_server)
                self.imap_client.login(self.sender_email, self.app_password)
                self.log("IMAP connection established and logged in.")

        except Exception as e:
            self.log_error(f"Error during connection setup: {e}")
            self.disconnect()
    def disconnect(self):
        """Gracefully close SMTP and IMAP connections."""
        try:
            if self.smtp_client:
                self.smtp_client.quit()
                self.smtp_client = None
                self.log("SMTP client disconnected.")

            if self.imap_client:
                self.imap_client.logout()
                self.imap_client = None
                self.log("IMAP client disconnected.")

        except Exception as e:
            self.log_error(f"Error during disconnection: {e}")
    def send(self, to: str, subject: str, body: str) -> bool:
        recipients = ", ".join([to])
        try:
            if not self.smtp_client:
                self.log("SMTP client disconnected, reconnecting...")
                self.connect()

            msg = MIMEText(body, "plain")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipients

            self.smtp_client.sendmail(self.sender_email, [to], msg.as_string())
            self.log(f"Email sent successfully to {recipients}")
            return True

        except (smtplib.SMTPServerDisconnected, smtplib.SMTPException) as e:
            self.log_error(f"SMTP error, attempting reconnect: {e}")
            self.disconnect()
            return False
        except Exception as e:
            self.log_error(f"General failure to send email: {e}")
            return False
    def read_emails(self, mailbox: str = "INBOX", search_criterion: str = "ALL"):
        """
        Example method to retrieve emails persistently.
        """
        try:
            if not self.imap_client:
                self.log("IMAP client disconnected, reconnecting...")
                self.connect()

            self.imap_client.select(mailbox)
            status, data = self.imap_client.search(None, search_criterion)

            email_ids = data[0].split()
            emails = []

            for email_id in email_ids:
                status, msg_data = self.imap_client.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    msg_data_0 = LIST.get(0, msg_data, [])
                    msg_data_1 = LIST.get(1, msg_data_0, None)
                    if not msg_data_1: continue
                    emails.append(msg_data_1)

            self.log(f"{len(emails)} emails retrieved.")
            return emails

        except imaplib.IMAP4.error as e:
            self.log_error(f"IMAP error: {e}")
            self.disconnect()
            return []
        except Exception as e:
            self.log_error(f"General error reading emails: {e}")
            return []

    def _fetch_emails_by_criterion(self, criterion: str, mailbox: str = "INBOX") -> List[EmailMessage]:
        """Generalized helper method for fetching emails by criterion."""
        emails = []
        try:
            if not self.imap_client:
                self.log("IMAP client disconnected, reconnecting...")
                self.connect()

            self.imap_client.select(mailbox)
            status, data = self.imap_client.search(None, criterion)

            email_ids = data[0].split()
            for email_id in email_ids:
                status, msg_data = self.imap_client.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    sender = email.utils.parseaddr(msg.get("From"))[1]
                    recipients = email.utils.getaddresses(msg.get_all("To", []))
                    subject = msg.get("Subject", "")
                    date = email.utils.parsedate_to_datetime(msg.get("Date"))
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    emails.append(self.EmailMessage(
                        sender=sender,
                        recipients=[addr[1] for addr in recipients],
                        subject=subject,
                        body=body,
                        date=date
                    ))

            self.log(f"{len(emails)} emails retrieved with criterion: {criterion}")
            return emails

        except Exception as e:
            self.log_error(f"Error fetching emails: {e}")
            self.disconnect()
            return []
    def get_emails_from_today(self) -> List[EmailMessage]:
        """Fetch emails received today."""
        today_str = datetime.now().strftime('%d-%b-%Y')
        criterion = f'(ON "{today_str}")'
        return self._fetch_emails_by_criterion(criterion)

    def get_emails_from_sender(self, sender_email: str) -> List[EmailMessage]:
        """Fetch emails from a specific sender."""
        criterion = f'(FROM "{sender_email}")'
        return self._fetch_emails_by_criterion(criterion)

    def get_last_n_emails(self, n: int = 10) -> List[EmailMessage]:
        """Fetch the last n emails from the inbox."""
        emails = []
        try:
            if not self.imap_client:
                self.log("IMAP client disconnected, reconnecting...")
                self.connect()

            self.imap_client.select("INBOX")
            status, data = self.imap_client.search(None, 'ALL')

            email_ids = data[0].split()
            latest_email_ids = email_ids[-n:]

            for email_id in latest_email_ids:
                status, msg_data = self.imap_client.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    sender = email.utils.parseaddr(msg.get("From"))[1]
                    recipients = email.utils.getaddresses(msg.get_all("To", []))
                    subject = msg.get("Subject", "")
                    date = email.utils.parsedate_to_datetime(msg.get("Date"))
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    emails.append(self.EmailMessage(
                        sender=sender,
                        recipients=[addr[1] for addr in recipients],
                        subject=subject,
                        body=body,
                        date=date
                    ))

            self.log(f"{len(emails)} last emails retrieved.")
            return emails

        except Exception as e:
            self.log_error(f"Error fetching last {n} emails: {e}")
            self.disconnect()
            return []

    # Additional recommended helper
    def delete_email_by_id(self, email_id: str, mailbox: str = "INBOX") -> bool:
        """Delete an email by its ID."""
        try:
            if not self.imap_client:
                self.log("IMAP client disconnected, reconnecting...")
                self.connect()

            self.imap_client.select(mailbox)
            self.imap_client.store(email_id, '+FLAGS', '\\Deleted')
            self.imap_client.expunge()

            self.log(f"Email with ID {email_id} deleted successfully.")
            return True
        except Exception as e:
            self.log_error(f"Error deleting email ID {email_id}: {e}")
            self.disconnect()
            return False
    def __del__(self):
        """Ensure cleanup on object deletion."""
        self.disconnect()

# Example usage:
if __name__ == '__main__':
    # Initialize the GmailClient
    email_client = cEmail()
    email_client.connect()
    success = email_client.get_last_n_emails()
    print(success)