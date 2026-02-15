import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.models import ConversationMessage
from backend.services.deepgram import transcribe_audio_deepgram
from backend.services.sentiment import analyze_sentiment_deepgram, analyze_sentiment_from_text
from backend.services.trello import create_trello_ticket
from backend.services.conversation import (
    classify_intent,
    get_knowledge_response,
    ESCALATION_RESPONSE,
    FAREWELL_RESPONSE,
)
from backend.store import conversations_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["voice"])


@router.post("/voice")
async def process_voice(conversation_id: str, audio: UploadFile = File(...)):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    audio_data = await audio.read()
    logger.info(f"Received audio: {len(audio_data)} bytes, content_type={audio.content_type}")

    transcript, sentiment_result = await asyncio.gather(
        transcribe_audio_deepgram(audio_data),
        analyze_sentiment_deepgram(audio_data),
    )

    logger.info(f"Transcript: '{transcript}'")
    logger.info(
        f"Audio sentiment: {sentiment_result.sentiment} "
        f"(confidence={sentiment_result.confidence}, details={sentiment_result.details})"
    )

    if not transcript:
        return {
            "error": "Could not transcribe audio. Please try again or type your message.",
        }

    if sentiment_result.sentiment == "neutral" and transcript:
        text_sentiment = analyze_sentiment_from_text(transcript)
        logger.info(
            f"Text sentiment fallback: {text_sentiment.sentiment} "
            f"(confidence={text_sentiment.confidence}, details={text_sentiment.details})"
        )
        if text_sentiment.sentiment == "negative":
            sentiment_result = text_sentiment
            sentiment_result.details = (
                f"Text fallback (audio returned neutral): {text_sentiment.details}"
            )

    now = datetime.now().isoformat()
    conv_data["messages"].append(
        ConversationMessage(
            role="user", content=transcript, timestamp=now
        ).model_dump()
    )

    query_type, topic = classify_intent(transcript)
    topic_label = topic.replace("_", " ").title()

    if query_type == "farewell":
        conv_data["status"] = "closed"
        conv_data["resolution_status"] = "ai_resolved"
        if conv_data.get("title") == "New Support Session":
            conv_data["title"] = "Support Session"
        conv_data["summary"] = "Customer ended conversation via voice. Query resolved by AI agent."

        conv_data["messages"].append(
            ConversationMessage(
                role="assistant",
                content=FAREWELL_RESPONSE,
                timestamp=datetime.now().isoformat(),
            ).model_dump()
        )

        ticket_id = await create_trello_ticket(
            title=f"Resolved: {conv_data.get('title', 'Support Session')}",
            description=(
                f"Voice session completed normally.\n"
                f"Transcript: {transcript}\n"
                f"Audio Sentiment: {sentiment_result.sentiment.upper()} "
                f"(confidence: {sentiment_result.confidence:.0%})\n"
                f"Resolution: Customer ended conversation"
            ),
        )
        conv_data["ticket_id"] = ticket_id
        conversations_store[conversation_id] = conv_data

        return {
            "conversation": conv_data,
            "sentiment": sentiment_result.model_dump(),
            "transcript": transcript,
            "response": FAREWELL_RESPONSE,
        }

    if sentiment_result.sentiment == "negative":
        conv_data["sentiment"] = "negative"
        conv_data["status"] = "closed"
        conv_data["escalated"] = True
        conv_data["ticket_type"] = "complaint"
        conv_data["resolution_status"] = "human_followup_required"
        conv_data["title"] = topic_label

        conv_data["messages"].append(
            ConversationMessage(
                role="assistant",
                content=ESCALATION_RESPONSE,
                timestamp=datetime.now().isoformat(),
            ).model_dump()
        )

        ticket_id = await create_trello_ticket(
            title=f"ESCALATED: {topic_label}",
            description=(
                f"Voice Query Transcript: {transcript}\n\n"
                f"Audio Sentiment: NEGATIVE "
                f"(confidence: {sentiment_result.confidence:.0%})\n"
                f"Analysis: {sentiment_result.details}\n"
                f"Escalation: YES\n"
                f"Human follow-up required within 30 minutes"
            ),
            labels=["urgent"],
            resolved=False,
        )

        conv_data["ticket_id"] = ticket_id
        conv_data["summary"] = (
            f"Voice query about {topic.replace('_', ' ')}. "
            f"Negative sentiment detected via Deepgram Audio Intelligence. Escalated."
        )

        conversations_store[conversation_id] = conv_data

        return {
            "conversation": conv_data,
            "sentiment": sentiment_result.model_dump(),
            "transcript": transcript,
            "response": ESCALATION_RESPONSE,
        }

    response_text = get_knowledge_response(topic)
    response_text += "\n\nIs there anything else I can help you with?"

    conv_data["sentiment"] = (
        "mixed" if sentiment_result.sentiment == "mixed"
        else "positive" if sentiment_result.sentiment == "positive"
        else "neutral"
    )
    conv_data["ticket_type"] = query_type
    conv_data["title"] = topic_label
    conv_data["resolution_status"] = "ai_resolved"

    conv_data["messages"].append(
        ConversationMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )

    ticket_id = await create_trello_ticket(
        title=f"{query_type.title()}: {topic_label}",
        description=(
            f"Voice Query Transcript: {transcript}\n\n"
            f"Audio Sentiment: {sentiment_result.sentiment.upper()} "
            f"(confidence: {sentiment_result.confidence:.0%})\n"
            f"Analysis: {sentiment_result.details}\n"
            f"Query Type: {query_type.upper()}\n"
            f"Topic: {topic_label}\n"
            f"Resolution: AI Resolved"
        ),
    )
    conv_data["ticket_id"] = ticket_id
    conv_data["summary"] = (
        f"Voice query about {topic.replace('_', ' ')}. "
        f"Audio sentiment: {sentiment_result.sentiment}. Resolved by AI agent."
    )

    conversations_store[conversation_id] = conv_data

    return {
        "conversation": conv_data,
        "sentiment": sentiment_result.model_dump(),
        "transcript": transcript,
        "response": response_text,
    }
