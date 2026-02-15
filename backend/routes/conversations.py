from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.models import (
    Conversation,
    ConversationMessage,
    TextQueryRequest,
    SentimentResult,
)
from backend.services.sentiment import analyze_sentiment_from_text
from backend.services.trello import create_trello_ticket
from backend.services.conversation import (
    classify_intent,
    get_knowledge_response,
    ESCALATION_RESPONSE,
    FAREWELL_RESPONSE,
)
from backend.store import conversations_store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

GREETING_MESSAGE = (
    "Hello! I'm your Assist Link support agent. "
    "How can I help you with your credit card today?"
)


@router.post("/start")
async def start_conversation():
    conv_id = f"conv-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.now().isoformat()

    conversation = Conversation(
        id=conv_id,
        title="New Support Session",
        status="active",
        sentiment="neutral",
        ticket_type="informational",
        resolution_status="in_progress",
        messages=[
            ConversationMessage(
                role="assistant",
                content=GREETING_MESSAGE,
                timestamp=now,
            )
        ],
        created_at=now,
    )

    conversations_store[conv_id] = conversation.model_dump()
    return conversation.model_dump()


@router.post("/message")
async def process_message(request: TextQueryRequest):
    conv_data = conversations_store.get(request.conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    now = datetime.now().isoformat()
    conv_data["messages"].append(
        ConversationMessage(
            role="user", content=request.message, timestamp=now
        ).model_dump()
    )

    sentiment_result = analyze_sentiment_from_text(request.message)
    query_type, topic = classify_intent(request.message)
    topic_label = topic.replace("_", " ").title()

    if query_type == "farewell":
        response_text = _handle_farewell(conv_data)
        ticket_desc = (
            f"Session completed normally.\n"
            f"Messages: {len(conv_data['messages'])}\n"
            f"Sentiment: {sentiment_result.sentiment.upper()}\n"
            f"Resolution: Customer ended conversation - AI Resolved"
        )
        ticket_id = await create_trello_ticket(
            title=f"Resolved: {conv_data.get('title', 'Support Session')}",
            description=ticket_desc,
        )
        conv_data["ticket_id"] = ticket_id
    elif sentiment_result.sentiment == "negative":
        response_text = _handle_escalation(conv_data, topic, topic_label)
        ticket_desc = (
            f"Customer Query: {request.message}\n\n"
            f"Sentiment: NEGATIVE - Dissatisfaction detected\n"
            f"Escalation: YES - Human follow-up required within 30 minutes\n"
            f"Query Type: {query_type.upper()}\n"
            f"Topic: {topic_label}"
        )
        ticket_id = await create_trello_ticket(
            title=f"ESCALATED: {topic_label}",
            description=ticket_desc,
            labels=["urgent", "escalated"],
        )
        conv_data["ticket_id"] = ticket_id
        conv_data["summary"] = (
            f"Customer reported {topic.replace('_', ' ')} and showed dissatisfaction. "
            f"Escalated to human agent."
        )
    else:
        response_text = _handle_resolved(conv_data, sentiment_result, query_type, topic, topic_label)
        ticket_desc = (
            f"Customer Query: {request.message}\n\n"
            f"Sentiment: {sentiment_result.sentiment.upper()}\n"
            f"Query Type: {query_type.upper()}\n"
            f"Topic: {topic_label}\n"
            f"Resolution: AI Resolved"
        )
        ticket_id = await create_trello_ticket(
            title=f"{query_type.title()}: {topic_label}",
            description=ticket_desc,
        )
        conv_data["ticket_id"] = ticket_id
        conv_data["summary"] = (
            f"User asked about {topic.replace('_', ' ')}. Query resolved by AI agent."
        )

    conversations_store[request.conversation_id] = conv_data

    return {
        "conversation": conv_data,
        "sentiment": sentiment_result.model_dump(),
        "response": conv_data["messages"][-1]["content"],
    }


@router.post("/{conversation_id}/close")
async def close_conversation(conversation_id: str):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_data["status"] = "closed"

    if not conv_data.get("ticket_id"):
        ticket_id = await create_trello_ticket(
            title=f"Session: {conv_data.get('title', 'Support Session')}",
            description=(
                f"Conversation closed.\n"
                f"Messages: {len(conv_data['messages'])}\n"
                f"Sentiment: {conv_data.get('sentiment', 'neutral')}\n"
                f"Resolution: {conv_data.get('resolution_status', 'ai_resolved')}"
            ),
        )
        conv_data["ticket_id"] = ticket_id

    conversations_store[conversation_id] = conv_data
    return conv_data


@router.get("")
async def get_conversations():
    convs = list(conversations_store.values())
    convs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return convs


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv_data


def _handle_farewell(conv_data: dict) -> str:
    conv_data["status"] = "closed"
    conv_data["resolution_status"] = "ai_resolved"
    if conv_data.get("title") == "New Support Session":
        conv_data["title"] = "Support Session"
    conv_data["summary"] = "Customer ended conversation. Query resolved by AI agent."

    conv_data["messages"].append(
        ConversationMessage(
            role="assistant",
            content=FAREWELL_RESPONSE,
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )

    return FAREWELL_RESPONSE


def _handle_escalation(conv_data: dict, topic: str, topic_label: str) -> str:
    conv_data["sentiment"] = "negative"
    conv_data["status"] = "escalated"
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

    return ESCALATION_RESPONSE


def _handle_resolved(
    conv_data: dict,
    sentiment_result: SentimentResult,
    query_type: str,
    topic: str,
    topic_label: str,
) -> str:
    conv_data["sentiment"] = "mixed" if sentiment_result.sentiment == "mixed" else "positive"
    conv_data["ticket_type"] = query_type
    conv_data["title"] = topic_label
    conv_data["resolution_status"] = "ai_resolved"

    response_text = get_knowledge_response(topic)
    response_text += "\n\nIs there anything else I can help you with?"

    conv_data["messages"].append(
        ConversationMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat(),
        ).model_dump()
    )

    return response_text
