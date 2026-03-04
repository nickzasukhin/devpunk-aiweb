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

CRITICAL LANGUAGE RULE: Detect the language of each user message and ALWAYS reply in that exact language.
- If user speaks Russian → reply in Russian
- If user speaks English → reply in English
Never switch languages unless the user switches first.
"""

# Language instruction appended to ANY custom prompt from DB
VOICE_LANGUAGE_INSTRUCTION = """

CRITICAL LANGUAGE RULE: Detect the language of each user message and ALWAYS reply in that exact language.
- If user speaks Russian → reply in Russian
- If user speaks English → reply in English
Never switch languages unless the user switches first."""

VOICE_FIRST_MESSAGE_DEFAULT = "Hi! I'm the DevPunks AI assistant. How can I help you today?"


def _get_config_value(db: Session, key: str):
    from database import Config
    cfg = db.query(Config).filter(Config.key == key).first()
    return cfg.value if cfg else None


def _build_voice_config(db: Session) -> dict:
    """Build Vapi voice config based on voice_provider setting in DB."""
    voice_provider = _get_config_value(db, "voice_provider") or "vapi"

    if voice_provider == "elevenlabs":
        el_key = _get_config_value(db, "elevenlabs_api_key") or settings.ELEVENLABS_API_KEY
        el_voice = _get_config_value(db, "elevenlabs_voice_id") or settings.ELEVENLABS_VOICE_ID
        if el_key and el_voice:
            return {
                "provider": "11labs",
                "voiceId": el_voice,
                "model": _get_config_value(db, "elevenlabs_model") or settings.ELEVENLABS_MODEL,
                "stability": float(_get_config_value(db, "elevenlabs_stability") or settings.ELEVENLABS_STABILITY),
                "similarityBoost": float(_get_config_value(db, "elevenlabs_similarity_boost") or settings.ELEVENLABS_SIMILARITY_BOOST),
                "style": float(_get_config_value(db, "elevenlabs_style") or settings.ELEVENLABS_STYLE),
            }

    # Default: Vapi built-in voice
    vapi_voice_id = _get_config_value(db, "vapi_voice_id") or "Elliot"
    vapi_speed_raw = _get_config_value(db, "vapi_voice_speed")
    voice_cfg: dict = {"provider": "vapi", "voiceId": vapi_voice_id}
    if vapi_speed_raw:
        voice_cfg["speed"] = float(vapi_speed_raw)
    return voice_cfg


def _build_model_config(db: Session, system_prompt: str) -> dict:
    """Build Vapi model config based on LLM provider setting in DB."""
    llm_provider = _get_config_value(db, "llm_provider") or settings.LLM_PROVIDER
    llm_model = _get_config_value(db, "llm_model") or settings.OPENAI_MODEL

    # Always append language rule so LLM responds in user's language
    full_prompt = system_prompt + VOICE_LANGUAGE_INSTRUCTION

    if llm_provider == "openai":
        return {
            "provider": "openai",
            "model": llm_model,
            "messages": [{"role": "system", "content": full_prompt}],
        }
    return {
        "provider": "anthropic",
        "model": settings.ANTHROPIC_MODEL,
        "messages": [{"role": "system", "content": full_prompt}],
    }


@router.get("/config")
async def get_voice_config(db: Session = Depends(get_db)):
    """Return Vapi assistant config for the browser SDK (no auth required)."""
    system_prompt = _get_config_value(db, "voice_system_prompt") or VOICE_PROMPT_DEFAULT
    first_message = _get_config_value(db, "voice_first_message") or VOICE_FIRST_MESSAGE_DEFAULT

    return {
        "transcriber": {
            "provider": "gladia",  # multilingual auto-detection (EN + RU + others)
        },
        "model": _build_model_config(db, system_prompt),
        "voice": _build_voice_config(db),
        "firstMessage": first_message,
        "serverUrl": "https://api.devpunks.io/api/voice/webhook",
        # Prevent user from accidentally interrupting the AI response
        "stopSpeakingPlan": {
            "numWords": 3,
            "voiceSeconds": 0.4,
            "backoffSeconds": 1.5,
        },
    }


@router.post("/webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Vapi.ai webhook for voice agent interactions."""
    body = await request.json()
    message_type = body.get("message", {}).get("type")

    # Server message — provide system prompt and tools
    if message_type == "assistant-request":
        system_prompt = _get_config_value(db, "voice_system_prompt") or VOICE_PROMPT_DEFAULT
        first_message = _get_config_value(db, "voice_first_message") or VOICE_FIRST_MESSAGE_DEFAULT

        return {
            "assistant": {
                "model": _build_model_config(db, system_prompt),
                "voice": _build_voice_config(db),
                "firstMessage": first_message,
            }
        }

    # End of call — save conversation
    if message_type == "end-of-call-report":
        _save_voice_conversation(db, body)
        return {"status": "ok"}

    return {"status": "ok"}


def _save_voice_conversation(db: Session, body: dict):
    # Vapi wraps all end-of-call-report data inside body["message"]
    msg = body.get("message", {})
    call = msg.get("call", {})
    transcript = msg.get("transcript", "")
    audio_url = msg.get("recordingUrl")
    messages_data = msg.get("artifact", {}).get("messages", msg.get("messages", []))

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
