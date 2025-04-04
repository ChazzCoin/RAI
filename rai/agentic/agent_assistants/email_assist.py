from typing import Type, List, Any

from rai.agentic.agent_modules.engine import register_tool_engine, ToolEngine
from rai.agentic.agent_modules.result import ToolResult
from rai.ingest.clients.email_client import cEmail


@register_tool_engine('email')
class EmailTool(ToolEngine):

    @staticmethod
    def tool_assistant_name() -> str: return "email"

    @staticmethod
    def assistant_rules() -> str:
        return """
            You understand users natural language and convert it into function calls related to email tasks.
            Tasks include: sending emails, retrieving recent emails, reading from specific senders or dates, and deleting emails.
            Don't over do the task. If the user wants an email sent, compose the email, send it, finish. Don't do more than needed.
        """

    def _required_data_model_type(self) -> Type[cEmail.EmailMessage]: return cEmail.EmailMessage

    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool('send_email'),
            self.get_tool('get_last_n_emails'),
            self.get_tool('get_emails_from_today'),
            self.get_tool('get_emails_from_sender'),
            self.get_tool('finish')
        ]

    def finish(self, **kwargs): return self.finish_and_then_respond()
    def send_email(self, to: str, subject: str, body: str) -> ToolResult:
        """
        Send an email using SMTP.
        Params:
            - to: Recipient email address.
            - subject: Email subject line.
            - body: Content of the email.
        """
        try:
            email_client = cEmail()
            email_client.connect()
            result: bool = email_client.send(to=to, subject=subject, body=body)
            email_client.disconnect()
            return ToolResult(
                output=f"Email sent to: [ {to} ].",
                success=result
            )
        except Exception as e:
            return ToolResult(
                output=f"Error during attempt to send email: {e}",
                success=False
            )
    def get_last_n_emails(self, n: int = 5) -> ToolResult:
        """
        Retrieve the last N emails from the inbox.
        Params:
            - n: Number of recent emails to retrieve (default: 5).
        """
        try:
            email_client = cEmail()
            email_client.connect()
            emails = email_client.get_last_n_emails(n=n)
            email_client.disconnect()

            if not emails:
                return ToolResult(
                    output="No emails found.",
                    success=True
                )

            summary = "\n\n".join([
                f"From: {email.sender}\nSubject: {email.subject}\nDate: {email.date.strftime('%Y-%m-%d %H:%M')}"
                for email in emails
            ])

            return ToolResult(
                output=f"Retrieved {len(emails)} recent email(s):\n\n{summary}",
                success=True
            )

        except Exception as e:
            return ToolResult(
                output=f"Failed to retrieve recent emails: {e}",
                success=False
            )
    def get_emails_from_today(self) -> ToolResult:
        """
        Retrieve all emails received today.
        """
        try:
            email_client = cEmail()
            email_client.connect()
            emails = email_client.get_emails_from_today()
            email_client.disconnect()

            if not emails:
                return ToolResult(
                    output="No emails received today.",
                    success=True
                )

            summary = "\n\n".join([
                f"From: {email.sender}\nSubject: {email.subject}\nDate: {email.date.strftime('%Y-%m-%d %H:%M')}"
                for email in emails
            ])

            return ToolResult(
                output=f"Retrieved {len(emails)} email(s) from today:\n\n{summary}",
                success=True
            )

        except Exception as e:
            return ToolResult(
                output=f"Failed to retrieve today's emails: {e}",
                success=False
            )
    def get_emails_from_sender(self, sender_email: str) -> ToolResult:
        """
        Retrieve all emails from a specific sender.
        Params:
            - sender_email: The sender's email address to filter by.
        """
        try:
            email_client = cEmail()
            email_client.connect()
            emails = email_client.get_emails_from_sender(sender_email=sender_email)
            email_client.disconnect()

            if not emails:
                return ToolResult(
                    output=f"No emails found from: {sender_email}.",
                    success=True
                )

            summary = "\n\n".join([
                f"From: {email.sender}\nSubject: {email.subject}\nDate: {email.date.strftime('%Y-%m-%d %H:%M')}"
                for email in emails
            ])

            return ToolResult(
                output=f"Retrieved {len(emails)} email(s) from {sender_email}:\n\n{summary}",
                success=True
            )

        except Exception as e:
            return ToolResult(
                output=f"Failed to retrieve emails from {sender_email}: {e}",
                success=False
            )
