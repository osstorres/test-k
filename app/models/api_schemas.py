from typing import Optional
from pydantic import BaseModel, Field


class KavakQueryRequest(BaseModel):
    query: str = Field(..., description="User query/message")
    user_id: Optional[str] = Field(None, description="User ID for memory context")


class KavakQueryResponse(BaseModel):
    response: str = Field(..., description="Agent response message")
    user_id: Optional[str] = Field(None, description="User ID")
    agent: str = Field(..., description="Agent name")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="LLM model used")


class TwilioWebhookEvent(BaseModel):
    MessageSid: str = Field(..., description="Twilio message SID")
    AccountSid: str = Field(..., description="Twilio account SID")
    From: str = Field(..., description="Sender phone number")
    To: str = Field(..., description="Recipient phone number")
    Body: str = Field(..., description="Message body")
    ProfileName: Optional[str] = Field(None, description="Sender profile name")
    NumMedia: str = Field("0", description="Number of media attachments")

    @property
    def user_id(self) -> str:
        return self.From.replace("whatsapp:", "")

    @property
    def message(self) -> str:
        return self.Body.strip()
