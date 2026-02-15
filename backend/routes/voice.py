import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.models import ConversationMessage
from backend.services.deepgram import transcribe_audio_deepgram
from backend.services.sentiment import analyze_sentiment_deepgram
from backend.services.trello import create_trello_ticket
from backend.services.conversation import classify_intent, ESCALATION_RESPONSE
from backend.store import conversations_store

router = APIRouter(prefix="/api/conversations", tags=["voice"])


@router.post("/voice")
async def process_voice(conversation_id: str, audio: UploadFile = File(...)):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    audio_data = await audio.read()

    transcript, sentiment_result = await asyncio.gather(
        transcribe_audio_deepgram(audio_data),
        analyze_sentiment_deepgram(audio_data),
    )

    if not transcript:
        return {
            "error": "Could not transcribe audio. Please try again or type your message.",
        }

    if sentiment_result.sentiment == "negative":
        now = datetime.now().isoformat()

        conv_data["messages"].append(
            ConversationMessage(
                role="user", content=transcript, timestamp=now
            ).model_dump()
        )

        conv_data["sentiment"] = "negative"
        conv_data["status"] = "escalated"
        conv_data["escalated"] = True
        conv_data["ticket_type"] = "complaint"
        conv_data["resolution_status"] = "human_followup_required"

        conv_data["messages"].append(
            ConversationMessage(
                role="assistant",
                content=ESCALATION_RESPONSE,
                timestamp=datetime.now().isoformat(),
            ).model_dump()
        )

        _, topic = classify_intent(transcript)
        topic_label = topic.replace("_", " ").title()

        ticket_id = await create_trello_ticket(
            title=f"ESCALATED: {topic_label}",
            description=(
                f"Voice Query Transcript: {transcript}\n\n"
                f"Sentiment: NEGATIVE (Audio Analysis)\n"
                f"Escalation: YES\n"
                f"Human follow-up required within 30 minutes"
            ),
            labels=["urgent"],
        )

        conv_data["ticket_id"] = ticket_id
        conv_data["title"] = topic_label
        conv_data["summary"] = (
            f"Voice query about {topic.replace('_', ' ')}. "
            f"Negative sentiment detected via audio analysis. Escalated."
        )

        conversations_store[conversation_id] = conv_data

        return {
            "conversation": conv_data,
            "sentiment": sentiment_result.model_dump(),
            "transcript": transcript,
            "response": ESCALATION_RESPONSE,
        }

    from backend.routes.conversations import process_message
    from backend.models import TextQueryRequest

    text_request = TextQueryRequest(
        conversation_id=conversation_id,
        message=transcript,
    )

    result = await process_message(text_request)
    result["transcript"] = transcript
    result["sentiment"] = sentiment_result.model_dump()
    return result
