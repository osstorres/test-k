from typing import Optional
from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config.logging import logger
from app.core.dependencies import KavakFacadeDep
from app.models.api.api_schemas import TwilioWebhookEvent


router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post(
    "/webhook",
    summary="Twilio WhatsApp webhook",
    description="Receives incoming WhatsApp messages from Twilio and processes them with Kavak agent.",
)
async def whatsapp_webhook(
    facade: KavakFacadeDep,
    MessageSid: str = Form(...),
    AccountSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    ProfileName: Optional[str] = Form(None),
    NumMedia: str = Form("0"),
) -> Response:
    try:
        event = TwilioWebhookEvent(
            MessageSid=MessageSid,
            AccountSid=AccountSid,
            From=From,
            To=To,
            Body=Body,
            ProfileName=ProfileName,
            NumMedia=NumMedia,
        )

        user_id = event.user_id
        message = event.message
        profile_name = event.ProfileName

        logger.info(
            f"Received WhatsApp message from {user_id} "
            f"(Profile: {profile_name or 'N/A'})"
        )

        if not message:
            logger.warning(f"Received empty message from {user_id}")
            twiml_response = MessagingResponse()
            twiml_response.message("Por favor, envía un mensaje válido.")
            twiml_xml = str(twiml_response)
            return Response(content=twiml_xml, media_type="text/xml", status_code=200)

        logger.info(f"Processing message with Kavak agent for user {user_id}")
        result = await facade.process_query(
            query=message,
            user_id=user_id,
        )

        agent_response = result.get(
            "response", "Lo siento, no pude procesar tu mensaje."
        )

        twiml_response = MessagingResponse()
        twiml_response.message(agent_response)
        twiml_xml = str(twiml_response)

        return Response(content=twiml_xml, media_type="text/xml", status_code=200)

    except Exception as exc:
        logger.error(f"Error processing WhatsApp webhook: {exc}", exc_info=True)

        twiml_response = MessagingResponse()
        twiml_response.message(
            "Lo siento, ocurrió un error al procesar tu mensaje. "
            "Por favor, intenta de nuevo más tarde."
        )
        twiml_xml = str(twiml_response)
        logger.error(f"Error TwiML response: {twiml_xml}")

        return Response(content=twiml_xml, media_type="text/xml", status_code=200)
