from typing import List, Type, Any
from pydantic import BaseModel
from rai import ToolEngine
from rai.agentic.agent_modules.engine import register_tool_engine

"""
- You are given 'TemplateTool' which is a template class giving you everything you need to build agent tools.
- You are given 'BaseClient' class that you will wrap as a Tool with a robust set of core functions needed.
1. Modify whats provided to fit the desired naming scheme.
2. Add new class functions that are specifically designed/setup to be simple calls for AI's to make directly.
    a. Essentially This class sits on top or 'wraps' a base client class with base functions.
    b. This class then adds helper functions to do basic tasks.
    c. This class inherits 'ToolEngine' which gives this class the ability for an AI to take in user prompts and call the functions it needs to acomplish the task.
3. ALL FUNCTIONS ADD TO 'get_tools' MUST RETURN 'ToolResult'
    a. The 'holder' attribute is for 'storing' specifically modeled data results like Chromadb documents for the AI to return to the user.
    EXAMPLES:
    def get_ollama_models(self, **kwargs) -> ToolResult:
        models = self.think.OLLAMA.list_models()
        return ToolResult(
            output="I have grabbed the available ollama llm models.",
            result=str(models),
            success=True
        )
    def delete_page(self, doc_id: str) -> ToolResult:
        try:
            self.log_voice(f"Attempting to delete document with ID: {doc_id}")
            self.rStore().delete(f"{self.tool_plan.prefix}.pages", [doc_id])
            self.log_voice(f"Document with ID '{doc_id}' deleted.")
            return ToolResult(
                output=f"Document with ID '{doc_id}' deleted.",
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong. {e}",
                success=False
            )
    def attach_data_and_send_result(self, results) -> ToolResult:
        return ToolResult(
            output="We have attached data to the holder.",
            success=True,
            holding=self._required_data_model_type().__class__.__name__,
            holder=results
        )
        
5. BaseClient Example:
class BaseEmailClient(mLog):
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
        return
    def send_email(self, to: str, subject: str, body: str) -> bool:
        return
    def read_emails(self, mailbox: str = "INBOX", search_criterion: str = "ALL") -> List[EmailMessage]:
        return
        
    **GOAL**
    ## Take the user prompts provided prompt with the Template and Client and create a new Tool that wraps the client accordingly.
"""
@register_tool_engine('template')
class TemplateTool(ToolEngine):

    @staticmethod
    def tool_assistant_name() -> str: return "template"

    @staticmethod
    def assistant_rules() -> str:
        """ Specific Rules for the Tools Functionality """
        return f"""
            You understand users natural language and convert it into a function to call.
        """

    def _required_data_model_type(self) -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        return Type[BaseModel]

    def get_tools(self) -> List[dict[str, Any]]:
        """ Specifically add each function that is desired for the AI to have control over."""
        return [
            self.get_tool('finish')
        ]

    def finish(self, **kwargs):
        """ Default Function for allowing the AI to finish/end the task once complete. """
        return self.finish_and_then_respond()
