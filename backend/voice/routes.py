import hmac
import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db, Visitor, Conversation, Message, ChannelEnum, AgentEnum, MessageRoleEnum
from ingestion.embedder import search_similar
from config import settings

router = APIRouter(prefix="/api/voice", tags=["voice"])

VOICE_PROMPT_DEFAULT = """You are the DevPunks AI voice assistant. You represent DevPunks, an AI-first development company.

Keep your answers SHORT and conversational — this is a voice call, not a chat. 
No markdown formatting, no bullet points, no code snippets.
Use natural spoken language. Max 2-3 sentences per response.

You can discuss: who DevPunks is, our services, tech stack, cases, how to get in touch.
Respond in the same language the user speaks (Russian or English).
"""


@router.post("/webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Vapi.ai webhook for voice agent interactions."""
    body = await request.json()
    message_type = body.get("message", {}).get("type")

    # Server message — provide system prompt and tools
    if message_type == "assistant-request":
        system_prompt = _get_config_value(db, "voice_system_prompt") or VOICE_PROMPT_DEFAULT
        return {
            "assistant": {
                "model": {
                    "provider": "anthropic",
                    "model": settings.ANTHROPIC_MODEL,
                    "systemPrompt": system_prompt,
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": _get_config_value(db, "elevenlabs_voice_id") or settings.ELEVENLABS_VOICE_ID,
                    "model": _get_config_value(db, "elevenlabs_model") or settings.ELEVENLABS_MODEL,
                    "stability": float(_get_config_value(db, "elevenlabs_stability") or settings.ELEVENLABS_STABILITY),
                    "similarityBoost": float(_get_config_value(db, "elevenlabs_similarity_boost") or settings.ELEVENLABS_SIMILARITY_BOOST),
                    "style": float(_get_config_value(db, "elevenlabs_style") or settings.ELEVENLABS_STYLE),
                },
                "firstMessage": "Hi! I'm the DevPunks AI assistant. How can I help you today?",
            }
        }

    # End of call — save conversation
    if message_type == "end-of-call-report":
        _save_voice_conversation(db, body)
        return {"status": "ok"}

    return {"status": "ok"}


def _get_config_value(db: Session, key: str):
    from database import Config
    cfg = db.query(Config).filter(Config.key == key).first()
    return cfg.value if cfg else None


def _save_voice_conversation(db: Session, body: dict):
    call = body.get("call", {})
    transcript = body.get("transcript", "")
    audio_url = body.get("recordingUrl")
    messages_data = body.get("messages", [])

    # Find or create visitor by call ID
    call_id = call.get("id", str(uuid.uuid4()))
    visitor = db.query(Visitor).filter(Visitor.anonymous_id == f"voice:{call_id}").first()
    if not visitor:
        visitor = Visitor(
            id=uuid.uuid4(),
            anonymous_id=f"voice:{call_id}",
            metadata_={"channel": "voice", "call_id": call_id}
        )
        db.add(visitor)
        db.flush()

    conversation = Conversation(
        id=uuid.uuid4(),
        visitor_id=visitor.id,
        channel=ChannelEnum.voice,
        agent=AgentEnum.voice,
        ended_at=datetime.utcnow(),
        audio_url=audio_url
    )
    db.add(conversation)
    db.flush()

    for msg in messages_data:
        role = msg.get("role", "user")
        content = msg.get("message", msg.get("content", ""))
        if content:
            db.add(Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                role=MessageRoleEnum.user if role == "user" else MessageRoleEnum.assistant,
                content=content
            ))

    db.commit()
