import email
import imaplib
import datetime

from pydantic import BaseModel

from rai.agentic.ai_plugins.reason import rAssistantReasoningPlugin
from rai.ingest.utilities.TextUtils import TextProcessor

app_password = "cjgz bqwz xbzk gpzf"

import smtplib
import logging
# from email.mime.text import MIMEText
from typing import Optional, List, Type


class fEmail(BaseModel):
    """
    A Pydantic model representing an email.
    """
    id: Optional[str] = None
    sender: str
    recipients: List[str]
    subject: str
    body: str
    is_html: bool = False
    date: Optional[datetime.datetime] = None

class rEmailAssistant(rAssistantReasoningPlugin):
    """
    A robust client for sending and retrieving emails via Gmail's SMTP and IMAP servers using an app password.
    Utilizes EmailModel for input and output.
    """

    @staticmethod
    def _required_data_model_type() -> Type[fEmail]:
        return fEmail

    @classmethod
    def module_name(cls) -> str:
        return cls.__name__

    @staticmethod
    def assistant_rules() -> str:
        return """
            You are an email manager and assistant.
            You retrieve and send emails accordingly.
        """

    @staticmethod
    def response_model() -> Type[BaseModel]:
        return fEmail

    sender_email: str = "charleskromeo@gmail.com"
    app_password: str = app_password
    smtp_server: str = "smtp.gmail.com"
    imap_server: str = "imap.gmail.com"
    smtp_port: int = 587

    def __init__(self):
        """
        Initializes the GmailClient.

        :param sender_email: The Gmail address used to send/receive emails.
        :param app_password: The app-specific password generated from your Google Account.
        :param smtp_server: The SMTP server (default is 'smtp.gmail.com').
        :param smtp_port: The port for the SMTP server (default is 587).
        """
        # Set up a logger for the client
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    # def send_email(self, to:str, subject:str, body:str) -> bool:
    #     """
    #     Sends an email using the Gmail SMTP server using the provided fEmail model.
    #     def send_email(self, to:str, subject:str, body:str, timeout: Optional[int] = None) -> bool:
    #     """
    #     recipients = ", ".join([to])
    #     try:
    #
    #         mime_subtype = "plain"
    #         msg = MIMEText(body, mime_subtype)
    #         msg["Subject"] = subject
    #         msg["From"] = self.sender_email
    #         msg["To"] = recipients
    #
    #         with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
    #             server.starttls()
    #             server.login(self.sender_email, self.app_password)
    #             server.sendmail(self.sender_email, recipients, msg.as_string())
    #
    #         self.assistant_log(f"Email sent successfully to {recipients}")
    #         return True
    #     except Exception as e:
    #         self.assistant_error_log(f"Failed to send email to {recipients or 'Unknown'}. ERROR: [ {str(e)} ]")
    #         return False
    #
    # def __send_email_model(self, email_model: fEmail, timeout: Optional[int] = None) -> bool:
    #     """
    #     Sends an email using the Gmail SMTP server using the provided EmailModel.
    #     :param email_model: An instance of EmailModel containing the email details.
    #     :param timeout: Optional timeout for the SMTP connection in seconds.
    #     :return: True if the email was sent successfully, False otherwise.
    #     """
    #     try:
    #         mime_subtype = "html" if email_model.is_html else "plain"
    #         msg = MIMEText(email_model.body, mime_subtype)
    #         msg["Subject"] = email_model.subject
    #         msg["From"] = email_model.sender
    #         msg["To"] = ", ".join(email_model.recipients)
    #
    #         with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout) as server:
    #             server.starttls()
    #             server.login(self.sender_email, self.app_password)
    #             server.sendmail(email_model.sender, email_model.recipients, msg.as_string())
    #
    #         self.assistant_log(f"Email sent successfully to {str(email_model.recipients)}")
    #         return True
    #     except Exception as e:
    #         self.assistant_error_log(f"Failed to send email to {str(email_model.recipients)}. ERROR: [ {str(e)} ]")
    #         return False

    def _parse_email(self, msg: email.message.Message, mail_id: Optional[bytes] = None) -> fEmail:
        """
        Parses an email.message.Message object into an EmailModel.
        :param msg: The email.message.Message object.
        :param mail_id: Optional unique ID of the email.
        :return: An instance of EmailModel populated with the email data.
        """
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        recipients_header = msg.get("To", "")
        recipients = [addr.strip() for addr in recipients_header.split(",")] if recipients_header else []
        date_str = msg.get("Date", None)
        parsed_date = None
        if date_str:
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                parsed_date = None

        # Extract email body and determine if it's HTML or plain text.
        body = ""
        is_html = False
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    is_html = False
                    break
                elif content_type == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    is_html = True
                    break
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
            if content_type == "text/html":
                is_html = True

        return fEmail(
            id=mail_id.decode() if mail_id is not None else None,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body=TextProcessor.NORMALIZE_NEW_LINES(body),
            is_html=is_html,
            date=parsed_date
        )

    def get_emails(self, folder: str = "inbox", search_criteria: str = "ALL", limit: Optional[int] = None) -> List[fEmail]:
        """
        Retrieves emails from the specified folder using IMAP. If a limit is provided,
        returns only the last N emails, parsed as EmailModel objects.
        :param folder: The folder/mailbox to search in (default: "inbox").
        :param search_criteria: The IMAP search criteria (default: "ALL").
        :param limit: Optional maximum number of recent emails to return.
        :return: List of EmailModel instances.
        """
        emails_list: List[fEmail] = []
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
                mail.login(self.sender_email, self.app_password)
                mail.select(folder)
                status, data = mail.search(None, search_criteria)
                if status != 'OK':
                    self.logger.error("Failed to search emails with criteria: %s", search_criteria)
                    return emails_list

                mail_ids = data[0].split()
                # If limit is provided, get only the last N email IDs.
                if limit is not None:
                    mail_ids = mail_ids[-limit:]

                for mail_id in mail_ids:
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status != "OK":
                        self.logger.error("Failed to fetch email with ID: %s", mail_id)
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    parsed_email = self._parse_email(msg, mail_id)
                    emails_list.append(parsed_email)

                mail.logout()
            self.logger.info("Retrieved %d emails from folder: %s", len(emails_list), folder)
            return emails_list
        except Exception as e:
            self.logger.exception("Failed to retrieve emails: %s", str(e))
            return emails_list

    def get_unread_emails_last_48h(self, folder: str = "inbox") -> List[fEmail]:
        """
        Retrieves unread emails from the specified folder received within the last 48 hours.
        This function uses an IMAP search with a SINCE criteria to limit the results at the server side,
        reducing the amount of emails to fetch.

        :param folder: The mailbox folder to search in (default: "inbox").
        :return: List of EmailModel instances for unread emails from the last 48 hours.
        """
        emails_list: List[fEmail] = []
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        threshold = now_utc - datetime.timedelta(hours=48)
        # IMAP expects the SINCE date in the format "DD-MMM-YYYY"
        threshold_date_str = threshold.strftime("%d-%b-%Y")
        try:
            with imaplib.IMAP4_SSL(self.imap_server) as mail:
                mail.login(self.sender_email, self.app_password)
                mail.select(folder)
                # Search for UNSEEN emails since the threshold date.
                # Note: The SINCE filter only compares dates (not times), so further filtering is done below.
                status, data = mail.search(None, 'UNSEEN', 'SINCE', threshold_date_str)
                if status != 'OK':
                    self.logger.error("Failed to search unread emails with criteria: UNSEEN SINCE %s",
                                      threshold_date_str)
                    return emails_list

                mail_ids = data[0].split()
                for mail_id in mail_ids:
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status != "OK":
                        self.logger.error("Failed to fetch email with ID: %s", mail_id)
                        continue
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    parsed_email = self._parse_email(msg, mail_id)
                    # Filter again using the precise timestamp
                    if parsed_email.date and parsed_email.date >= threshold:
                        emails_list.append(parsed_email)
                mail.logout()
            self.logger.info("Retrieved %d unread emails from the last 48 hours in folder: %s", len(emails_list),
                             folder)
            return emails_list
        except Exception as e:
            self.logger.exception("Failed to retrieve unread emails: %s", str(e))
            return emails_list

# Example usage:
if __name__ == '__main__':
    # Initialize the GmailClient
    email_client = rEmailAssistant()
    success = email_client.reason(user_request="show me my latest unread emails")
    print(success)

