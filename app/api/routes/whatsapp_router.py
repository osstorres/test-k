from typing import Optional
import asyncio
from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient

from app.core.config.logging import logger
from app.core.dependencies import KavakFacadeDep
from app.core.manager import get_settings
from app.models.api.api_schemas import TwilioWebhookEvent

router = APIRouter(prefix="/mD0UNo976r64HlxkUQbLpp", tags=["whatsapp"])


async def send_whatsapp_message_async(
    to: str,
    from_number: str,
    message: str,
    account_sid: str,
    auth_token: str,
) -> None:
    """Send WhatsApp message using Twilio API asynchronously."""
    try:
        loop = asyncio.get_event_loop()
        client = TwilioClient(account_sid, auth_token)

        def send_message():
            return client.messages.create(
                body=message,
                from_=from_number,
                to=to,
            )

        result = await loop.run_in_executor(None, send_message)
        logger.info(
            f"Successfully sent WhatsApp message to {to}. Message SID: {result.sid}"
        )
    except Exception as exc:
        logger.error(f"Error sending WhatsApp message to {to}: {exc}", exc_info=True)
        raise


async def process_and_send_message(
    facade: KavakFacadeDep,
    user_id: str,
    message: str,
    profile_name: Optional[str],
    to_number: str,
    from_number: str,
    account_sid: str,
    auth_token: str,
) -> None:
    """Process message with agent and send response via Twilio API."""
    try:
        logger.info(f"Processing message with Kavak agent for user {user_id}")
        result = await facade.process_query(
            query=message,
            user_id=user_id,
        )

        logger.info(f"Agent result keys: {list(result.keys()) if result else 'None'}")
        logger.info(f"Agent result: {result}")

        agent_response = result.get(
            "response", "Lo siento, no pude procesar tu mensaje."
        )

        if not agent_response or not agent_response.strip():
            logger.warning(
                f"Empty agent response for user {user_id}, using default message"
            )
            agent_response = "Lo siento, no pude procesar tu mensaje."

        logger.info(
            f"Preparing WhatsApp message for user {user_id}. Response length: {len(agent_response)}"
        )
        logger.info(f"Agent response preview: {agent_response[:200]}...")

        await send_whatsapp_message_async(
            to=to_number,
            from_number=from_number,
            message=agent_response,
            account_sid=account_sid,
            auth_token=auth_token,
        )

        if facade.memory_manager and user_id:
            await facade.memory_manager.add_conversation_memory(
                user_id=user_id,
                query=message,
                answer=agent_response,
                metadata={"source": "whatsapp", "profile_name": profile_name},
            )

        logger.info(f"Successfully processed and sent message for user {user_id}")
    except Exception as exc:
        logger.error(
            f"Error processing and sending message for user {user_id}: {exc}",
            exc_info=True,
        )
        try:
            error_msg = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo más tarde."
            await send_whatsapp_message_async(
                to=to_number,
                from_number=from_number,
                message=error_msg,
                account_sid=account_sid,
                auth_token=auth_token,
            )
        except Exception as send_exc:
            logger.error(f"Failed to send error message: {send_exc}", exc_info=True)


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

        settings = get_settings()
        twilio_settings = settings.kavak.twilio

        if not twilio_settings.ACCOUNT_SID or not twilio_settings.AUTH_TOKEN:
            logger.error("Twilio credentials not configured")
            twiml_response = MessagingResponse()
            twiml_response.message(
                "Lo siento, el servicio no está configurado correctamente."
            )
            twiml_xml = str(twiml_response)
            return Response(content=twiml_xml, media_type="text/xml", status_code=200)

        twiml_response = MessagingResponse()
        twiml_xml = str(twiml_response)

        asyncio.create_task(
            process_and_send_message(
                facade=facade,
                user_id=user_id,
                message=message,
                profile_name=profile_name,
                to_number=From,
                from_number=twilio_settings.WHATSAPP_FROM or To,
                account_sid=twilio_settings.ACCOUNT_SID,
                auth_token=twilio_settings.AUTH_TOKEN,
            )
        )

        logger.info(
            f"Responded to Twilio webhook immediately, processing message asynchronously for user {user_id}"
        )
        return Response(content=twiml_xml, media_type="text/xml", status_code=200)

    except Exception as exc:
        logger.error(f"Error processing WhatsApp webhook: {exc}", exc_info=True)

        twiml_response = MessagingResponse()
        twiml_xml = str(twiml_response)

        return Response(content=twiml_xml, media_type="text/xml", status_code=200)
