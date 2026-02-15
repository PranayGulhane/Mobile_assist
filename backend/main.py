import os
import json
import httpx
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Assist Link API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversations_store: dict = {}

CREDIT_CARD_KNOWLEDGE = {
    "bill_generation": "Your credit card bill is generated on the 1st of every month. The billing cycle runs from the 1st to the last day of each month.",
    "payment_deduction": "Payment is automatically deducted 15 days after bill generation, on the 16th of each month from your registered bank account.",
    "outstanding_balance": "Your current outstanding balance can be checked in your monthly statement. For the most accurate balance, please check your latest statement or contact your bank directly.",
    "due_date": "Your payment due date is the 16th of every month. A grace period of 3 days is available until the 19th without late fees.",
    "double_deduction": "We understand your concern about a double deduction. This has been noted and will be investigated. A refund will be processed within 5-7 business days if confirmed.",
    "incorrect_billing": "We take incorrect billing seriously. Your complaint has been registered and our billing team will review your account within 24 hours.",
    "unauthorized_charge": "An unauthorized charge is a serious matter. We will immediately flag your account for review and our fraud team will investigate within 24 hours.",
    "missing_refund": "Refunds typically take 7-10 business days to process. If it has been longer, your case will be escalated for immediate review.",
}


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class Conversation(BaseModel):
    id: str
    title: str
    status: str
    sentiment: str
    ticket_id: Optional[str] = None
    ticket_type: str
    resolution_status: str
    messages: list[ConversationMessage]
    created_at: str
    summary: Optional[str] = None
    escalated: bool = False


class TextQueryRequest(BaseModel):
    conversation_id: str
    message: str


class CreateTicketRequest(BaseModel):
    conversation_id: str
    title: str
    description: str
    ticket_type: str
    sentiment: str
    escalated: bool
    resolution_status: str


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float
    details: str


def classify_intent(message: str) -> tuple[str, str]:
    message_lower = message.lower()

    complaint_keywords = ["double", "twice", "incorrect", "wrong", "unauthorized", "fraud", "missing refund", "not received", "overcharged", "charged twice", "error", "mistake"]
    for keyword in complaint_keywords:
        if keyword in message_lower:
            if "double" in message_lower or "twice" in message_lower:
                return "complaint", "double_deduction"
            elif "incorrect" in message_lower or "wrong" in message_lower:
                return "complaint", "incorrect_billing"
            elif "unauthorized" in message_lower or "fraud" in message_lower:
                return "complaint", "unauthorized_charge"
            elif "refund" in message_lower or "not received" in message_lower:
                return "complaint", "missing_refund"

    if "bill" in message_lower and ("generat" in message_lower or "when" in message_lower or "date" in message_lower):
        return "informational", "bill_generation"
    elif "payment" in message_lower and ("deduct" in message_lower or "when" in message_lower):
        return "informational", "payment_deduction"
    elif "balance" in message_lower or "outstanding" in message_lower or "owe" in message_lower:
        return "informational", "outstanding_balance"
    elif "due" in message_lower and ("date" in message_lower or "when" in message_lower):
        return "informational", "due_date"

    return "informational", "bill_generation"


def analyze_sentiment_from_text(message: str) -> SentimentResult:
    message_lower = message.lower()

    negative_words = ["angry", "frustrated", "annoyed", "terrible", "horrible", "worst", "hate", "ridiculous", "unacceptable", "disgusting", "furious", "outraged", "stupid", "useless", "pathetic", "scam", "fraud", "steal", "cheat", "liar", "incompetent", "never", "nothing", "waste"]
    strong_negative = ["furious", "outraged", "scam", "fraud", "steal", "cheat", "liar", "pathetic", "disgusting"]

    negative_count = sum(1 for word in negative_words if word in message_lower)
    strong_negative_count = sum(1 for word in strong_negative if word in message_lower)

    if strong_negative_count > 0 or negative_count >= 3:
        return SentimentResult(
            sentiment="negative",
            confidence=0.95,
            details="High dissatisfaction detected. Customer shows strong negative emotions."
        )
    elif negative_count >= 1:
        return SentimentResult(
            sentiment="mixed",
            confidence=0.7,
            details="Some frustration detected. Monitoring for escalation."
        )
    else:
        return SentimentResult(
            sentiment="positive",
            confidence=0.8,
            details="Customer appears calm and engaged."
        )


async def analyze_sentiment_deepgram(audio_data: bytes) -> SentimentResult:
    deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details="Sentiment analysis unavailable - API key not configured"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen?sentiment=true&language=en",
                headers={
                    "Authorization": f"Token {deepgram_api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                timeout=30.0,
            )
            if response.status_code == 200:
                result = response.json()
                sentiments = []
                channels = result.get("results", {}).get("channels", [])
                for channel in channels:
                    for alt in channel.get("alternatives", []):
                        for para in alt.get("paragraphs", {}).get("paragraphs", []):
                            for sentence in para.get("sentences", []):
                                sentiments.append(sentence.get("sentiment", "neutral"))

                if sentiments:
                    neg_count = sentiments.count("negative")
                    pos_count = sentiments.count("positive")
                    total = len(sentiments)

                    if neg_count / total > 0.5:
                        return SentimentResult(
                            sentiment="negative",
                            confidence=neg_count / total,
                            details=f"Detected negative sentiment in {neg_count}/{total} segments"
                        )
                    elif pos_count / total > 0.5:
                        return SentimentResult(
                            sentiment="positive",
                            confidence=pos_count / total,
                            details=f"Detected positive sentiment in {pos_count}/{total} segments"
                        )

                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.6,
                    details="Mixed or neutral sentiment detected"
                )
            else:
                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.5,
                    details=f"Sentiment API returned status {response.status_code}"
                )
    except Exception as e:
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details=f"Sentiment analysis error: {str(e)}"
        )


async def transcribe_audio_deepgram(audio_data: bytes) -> str:
    deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        return ""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&language=en",
                headers={
                    "Authorization": f"Token {deepgram_api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                timeout=30.0,
            )
            if response.status_code == 200:
                result = response.json()
                channels = result.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        return alternatives[0].get("transcript", "")
            return ""
    except Exception:
        return ""


async def create_trello_ticket(title: str, description: str, labels: list[str] = None) -> Optional[str]:
    trello_api_key = os.environ.get("TRELLO_API_KEY")
    trello_token = os.environ.get("TRELLO_TOKEN")
    trello_list_id = os.environ.get("TRELLO_LIST_ID")

    if not all([trello_api_key, trello_token, trello_list_id]):
        ticket_id = f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return ticket_id

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "key": trello_api_key,
                "token": trello_token,
                "idList": trello_list_id,
                "name": title,
                "desc": description,
            }
            response = await client.post(
                "https://api.trello.com/1/cards",
                params=params,
                timeout=15.0,
            )
            if response.status_code == 200:
                card = response.json()
                return card.get("id", ticket_id)
            else:
                return f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    except Exception:
        return f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Assist Link API"}


@app.post("/api/conversations/start")
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
                content="Hello! I'm your Assist Link support agent. How can I help you with your credit card today?",
                timestamp=now,
            )
        ],
        created_at=now,
    )

    conversations_store[conv_id] = conversation.model_dump()
    return conversation.model_dump()


@app.post("/api/conversations/message")
async def process_message(request: TextQueryRequest):
    conv_data = conversations_store.get(request.conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    now = datetime.now().isoformat()
    conv_data["messages"].append(
        ConversationMessage(role="user", content=request.message, timestamp=now).model_dump()
    )

    sentiment_result = analyze_sentiment_from_text(request.message)
    query_type, topic = classify_intent(request.message)

    if sentiment_result.sentiment == "negative":
        conv_data["sentiment"] = "negative"
        conv_data["status"] = "escalated"
        conv_data["escalated"] = True
        conv_data["ticket_type"] = "complaint"
        conv_data["resolution_status"] = "human_followup_required"

        response_text = "I understand your frustration, and I sincerely apologize for the inconvenience. A customer care executive will connect with you within 30 minutes to resolve this personally. Your concern has been escalated to our priority queue."

        conv_data["messages"].append(
            ConversationMessage(role="assistant", content=response_text, timestamp=datetime.now().isoformat()).model_dump()
        )

        ticket_title = f"ESCALATED: {topic.replace('_', ' ').title()}"
        ticket_desc = f"Customer Query: {request.message}\n\nSentiment: NEGATIVE - Dissatisfaction detected\nEscalation: YES - Human follow-up required within 30 minutes\nQuery Type: {query_type.upper()}\nTopic: {topic.replace('_', ' ').title()}"

        ticket_id = await create_trello_ticket(ticket_title, ticket_desc, ["urgent", "escalated"])
        conv_data["ticket_id"] = ticket_id
        conv_data["title"] = topic.replace("_", " ").title()
        conv_data["summary"] = f"Customer reported {topic.replace('_', ' ')} and showed dissatisfaction. Escalated to human agent."

    else:
        if sentiment_result.sentiment == "mixed":
            conv_data["sentiment"] = "mixed"
        else:
            conv_data["sentiment"] = "positive"

        conv_data["ticket_type"] = query_type

        response_text = CREDIT_CARD_KNOWLEDGE.get(topic, "I'd be happy to help you with that. Could you provide more details about your query?")
        response_text += "\n\nIs there anything else I can help you with?"

        conv_data["messages"].append(
            ConversationMessage(role="assistant", content=response_text, timestamp=datetime.now().isoformat()).model_dump()
        )

        conv_data["title"] = topic.replace("_", " ").title()
        conv_data["resolution_status"] = "ai_resolved"

        ticket_title = f"{query_type.title()}: {topic.replace('_', ' ').title()}"
        ticket_desc = f"Customer Query: {request.message}\n\nSentiment: {sentiment_result.sentiment.upper()}\nQuery Type: {query_type.upper()}\nTopic: {topic.replace('_', ' ').title()}\nResolution: AI Resolved"

        ticket_id = await create_trello_ticket(ticket_title, ticket_desc)
        conv_data["ticket_id"] = ticket_id
        conv_data["summary"] = f"User asked about {topic.replace('_', ' ')}. Query resolved by AI agent."

    conversations_store[request.conversation_id] = conv_data

    return {
        "conversation": conv_data,
        "sentiment": sentiment_result.model_dump(),
        "response": conv_data["messages"][-1]["content"],
    }


@app.post("/api/conversations/voice")
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
        return {"error": "Could not transcribe audio. Please try again or type your message."}

    text_request = TextQueryRequest(
        conversation_id=conversation_id,
        message=transcript,
    )

    if sentiment_result.sentiment == "negative":
        now = datetime.now().isoformat()
        conv_data["messages"].append(
            ConversationMessage(role="user", content=transcript, timestamp=now).model_dump()
        )
        conv_data["sentiment"] = "negative"
        conv_data["status"] = "escalated"
        conv_data["escalated"] = True
        conv_data["ticket_type"] = "complaint"
        conv_data["resolution_status"] = "human_followup_required"

        response_text = "I understand your frustration, and I sincerely apologize for the inconvenience. A customer care executive will connect with you within 30 minutes to resolve this personally."

        conv_data["messages"].append(
            ConversationMessage(role="assistant", content=response_text, timestamp=datetime.now().isoformat()).model_dump()
        )

        _, topic = classify_intent(transcript)
        ticket_title = f"ESCALATED: {topic.replace('_', ' ').title()}"
        ticket_desc = f"Voice Query Transcript: {transcript}\n\nSentiment: NEGATIVE (Audio Analysis)\nEscalation: YES\nHuman follow-up required within 30 minutes"

        ticket_id = await create_trello_ticket(ticket_title, ticket_desc, ["urgent"])
        conv_data["ticket_id"] = ticket_id
        conv_data["title"] = topic.replace("_", " ").title()
        conv_data["summary"] = f"Voice query about {topic.replace('_', ' ')}. Negative sentiment detected via audio analysis. Escalated."

        conversations_store[conversation_id] = conv_data

        return {
            "conversation": conv_data,
            "sentiment": sentiment_result.model_dump(),
            "transcript": transcript,
            "response": response_text,
        }

    result = await process_message(text_request)
    result["transcript"] = transcript
    result["sentiment"] = sentiment_result.model_dump()
    return result


@app.post("/api/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: str):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_data["status"] = "closed"

    if not conv_data.get("ticket_id"):
        ticket_title = f"Session: {conv_data.get('title', 'Support Session')}"
        ticket_desc = f"Conversation closed.\nMessages: {len(conv_data['messages'])}\nSentiment: {conv_data.get('sentiment', 'neutral')}\nResolution: {conv_data.get('resolution_status', 'ai_resolved')}"
        ticket_id = await create_trello_ticket(ticket_title, ticket_desc)
        conv_data["ticket_id"] = ticket_id

    conversations_store[conversation_id] = conv_data
    return conv_data


@app.get("/api/conversations")
async def get_conversations():
    convs = list(conversations_store.values())
    convs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return convs


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv_data = conversations_store.get(conversation_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv_data


@app.post("/api/sentiment/analyze")
async def analyze_sentiment_endpoint(audio: UploadFile = File(...)):
    audio_data = await audio.read()
    result = await analyze_sentiment_deepgram(audio_data)
    return result.model_dump()


@app.post("/api/sentiment/text")
async def analyze_text_sentiment(request: TextQueryRequest):
    result = analyze_sentiment_from_text(request.message)
    return result.model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
