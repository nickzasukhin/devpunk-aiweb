import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db, Visitor, Conversation, Message, Config, ChannelEnum, AgentEnum, MessageRoleEnum
from config import settings

router = APIRouter(prefix="/api/voice", tags=["voice"])

EL_API = "https://api.elevenlabs.io/v1"

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

VOICE_LANGUAGE_INSTRUCTION = """

CRITICAL LANGUAGE RULE: Detect the language of each user message and ALWAYS reply in that exact language.
- If user speaks Russian → reply in Russian
- If user speaks English → reply in English
Never switch languages unless the user switches first."""

VOICE_FIRST_MESSAGE_DEFAULT = "Hi! I'm the DevPunks AI assistant. How can I help you today?"


def _get_config_value(db: Session, key: str):
    cfg = db.query(Config).filter(Config.key == key).first()
    return cfg.value if cfg else None


def _set_config_value(db: Session, key: str, value: str):
    cfg = db.query(Config).filter(Config.key == key).first()
    if cfg:
        cfg.value = value
    else:
        db.add(Config(key=key, value=value))
    db.commit()


def _build_agent_body(system_prompt: str, first_message: str, voice_id: str, db: Session) -> dict:
    stability = float(_get_config_value(db, "elevenlabs_stability") or 0.5)
    similarity = float(_get_config_value(db, "elevenlabs_similarity_boost") or 0.8)
    style = float(_get_config_value(db, "elevenlabs_style") or 0.0)
    speed_raw = _get_config_value(db, "vapi_voice_speed")
    speed = float(speed_raw) if speed_raw else 1.0

    return {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": system_prompt,
                    "llm": "gemini-2.5-flash",  # built-in LLM, no extra key needed
                    "temperature": 0.7,
                    "max_tokens": -1,
                    "built_in_tools": {
                        # enables automatic EN/RU language switching mid-conversation
                        "language_detection": {
                            "name": "language_detection",
                            "params": {},
                        },
                    },
                },
                "first_message": first_message,
                # no language field = defaults to "en"; language_detection tool handles switching
            },
            "tts": {
                "voice_id": voice_id,
                "stability": stability,
                "similarity_boost": similarity,
                "style": style,
                "speed": speed,
            },
            "conversation": {
                "max_duration_seconds": 1800,
            },
        }
    }


async def _get_or_create_agent_id(db: Session, el_key: str, agent_body: dict) -> str:
    agent_id = _get_config_value(db, "elevenlabs_convai_agent_id")
    if not agent_id:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{EL_API}/convai/agents/create",
                headers={"xi-api-key": el_key},
                json={"name": "DevPunks Voice Agent", **agent_body},
                timeout=30.0,
            )
            resp.raise_for_status()
            agent_id = resp.json()["agent_id"]
        _set_config_value(db, "elevenlabs_convai_agent_id", agent_id)
    return agent_id


async def _update_agent(el_key: str, agent_id: str, agent_body: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{EL_API}/convai/agents/{agent_id}",
            headers={"xi-api-key": el_key},
            json=agent_body,
            timeout=30.0,
        )
        resp.raise_for_status()


async def _get_signed_url(el_key: str, agent_id: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EL_API}/convai/conversation/get_signed_url",
            headers={"xi-api-key": el_key},
            params={"agent_id": agent_id},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["signed_url"]


@router.get("/convai-token")
async def get_convai_token(db: Session = Depends(get_db)):
    """Return ElevenLabs Conversational AI signed WebSocket URL for browser SDK."""
    el_key = _get_config_value(db, "elevenlabs_api_key") or settings.ELEVENLABS_API_KEY
    if not el_key:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    system_prompt = _get_config_value(db, "voice_system_prompt") or VOICE_PROMPT_DEFAULT
    full_prompt = system_prompt + VOICE_LANGUAGE_INSTRUCTION
    first_message = _get_config_value(db, "voice_first_message") or VOICE_FIRST_MESSAGE_DEFAULT
    voice_id = _get_config_value(db, "elevenlabs_voice_id") or "JBFqnCBsd6RMkjVDRZzb"  # George fallback

    agent_body = _build_agent_body(full_prompt, first_message, voice_id, db)
    agent_id = await _get_or_create_agent_id(db, el_key, agent_body)
    await _update_agent(el_key, agent_id, agent_body)
    signed_url = await _get_signed_url(el_key, agent_id)

    return {"signedUrl": signed_url}


@router.post("/save-conversation")
async def save_conversation(request: Request, db: Session = Depends(get_db)):
    """Called by frontend after call ends — fetches transcript from ElevenLabs and saves to DB."""
    body = await request.json()
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        return {"status": "ok"}

    el_key = _get_config_value(db, "elevenlabs_api_key") or settings.ELEVENLABS_API_KEY
    if not el_key:
        return {"status": "ok"}

    # Wait briefly for ElevenLabs to finalize transcript
    import asyncio
    await asyncio.sleep(3)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EL_API}/convai/conversations/{conversation_id}",
            headers={"xi-api-key": el_key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return {"status": "ok"}
        data = resp.json()

    transcript = data.get("transcript", [])

    visitor = db.query(Visitor).filter(Visitor.anonymous_id == f"voice:{conversation_id}").first()
    if not visitor:
        visitor = Visitor(
            id=uuid.uuid4(),
            anonymous_id=f"voice:{conversation_id}",
            metadata_={"channel": "voice", "conversation_id": conversation_id},
        )
        db.add(visitor)
        db.flush()

    conversation = Conversation(
        id=uuid.uuid4(),
        visitor_id=visitor.id,
        channel=ChannelEnum.voice,
        agent=AgentEnum.voice,
        ended_at=datetime.utcnow(),
    )
    db.add(conversation)
    db.flush()

    for msg in transcript:
        role = msg.get("role", "user")
        content = msg.get("message", "")
        if content and role in ("agent", "user"):
            db.add(Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                role=MessageRoleEnum.user if role == "user" else MessageRoleEnum.assistant,
                content=content,
            ))

    db.commit()
    return {"status": "ok"}


# ── Legacy Vapi endpoints (kept for compatibility) ──────────────────────────

@router.get("/config")
async def get_voice_config(db: Session = Depends(get_db)):
    """Legacy Vapi config endpoint — no longer active."""
    return {"error": "Vapi deprecated, use /api/voice/convai-token"}


@router.post("/webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """Legacy Vapi webhook — saves any remaining end-of-call reports."""
    body = await request.json()
    message_type = body.get("message", {}).get("type")
    if message_type == "end-of-call-report":
        _save_vapi_conversation(db, body)
    return {"status": "ok"}


def _save_vapi_conversation(db: Session, body: dict):
    msg = body.get("message", {})
    call = msg.get("call", {})
    audio_url = msg.get("recordingUrl")
    messages_data = msg.get("artifact", {}).get("messages", msg.get("messages", []))

    call_id = call.get("id", str(uuid.uuid4()))
    visitor = db.query(Visitor).filter(Visitor.anonymous_id == f"voice:{call_id}").first()
    if not visitor:
        visitor = Visitor(
            id=uuid.uuid4(),
            anonymous_id=f"voice:{call_id}",
            metadata_={"channel": "voice", "call_id": call_id},
        )
        db.add(visitor)
        db.flush()

    conversation = Conversation(
        id=uuid.uuid4(),
        visitor_id=visitor.id,
        channel=ChannelEnum.voice,
        agent=AgentEnum.voice,
        ended_at=datetime.utcnow(),
        audio_url=audio_url,
    )
    db.add(conversation)
    db.flush()

    for m in messages_data:
        role = m.get("role", "user")
        content = m.get("message", m.get("content", ""))
        if content and role in ("user", "assistant"):
            db.add(Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                role=MessageRoleEnum.user if role == "user" else MessageRoleEnum.assistant,
                content=content,
            ))

    db.commit()
