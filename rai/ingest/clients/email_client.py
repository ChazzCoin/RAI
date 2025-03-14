from F import LIST

from rai.agentic.ai_modules import mLog
from rai.internal.connectors import AUTHORITY

import smtplib
import imaplib
from email.mime.text import MIMEText
from typing import Optional


class cEmail(mLog):
    smtp_client: Optional[smtplib.SMTP] = None
    imap_client: Optional[imaplib.IMAP4_SSL] = None

    sender_email: str = AUTHORITY.get_env("", "")
    app_password: str = AUTHORITY.get_env("", "")
    smtp_server: str = AUTHORITY.get_env("", "smtp.gmail.com")
    imap_server: str = AUTHORITY.get_env("", "imap.gmail.com")
    smtp_port: int = int(AUTHORITY.get_env("", 587))

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

    def send_email(self, to: str, subject: str, body: str) -> bool:
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

    def __del__(self):
        """Ensure cleanup on object deletion."""
        self.disconnect()
