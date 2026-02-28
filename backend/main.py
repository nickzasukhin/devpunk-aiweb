import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config import settings
from database import get_db, init_db, User, RoleEnum, Visitor, Conversation, Message, ChannelEnum, AgentEnum, MessageRoleEnum, Config
from auth.utils import hash_password
from auth.routes import router as auth_router
from admin.routes import router as admin_router
from voice.routes import router as voice_router
from agents.sales_agent import run_sales_agent_stream, SALES_PROMPT_DEFAULT

app = FastAPI(title="DevPunks AI API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(voice_router)


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    _seed_superadmin()


def _seed_superadmin():
    db = next(get_db())
    try:
        existing = db.query(User).filter(User.role == RoleEnum.superadmin).first()
        if not existing:
            existing_email = db.query(User).filter(User.email == settings.SUPERADMIN_EMAIL).first()
            if not existing_email:
                user = User(
                    id=uuid.uuid4(),
                    email=settings.SUPERADMIN_EMAIL,
                    hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
                    role=RoleEnum.superadmin,
                    is_active=True,
                )
                db.add(user)
                try:
                    db.commit()
                    print(f"[SEED] SuperAdmin created: {settings.SUPERADMIN_EMAIL}")
                except Exception:
                    db.rollback()
                    print(f"[SEED] SuperAdmin already exists (skipped)")
            else:
                # Promote existing user to superadmin
                existing_email.role = RoleEnum.superadmin
                db.commit()
                print(f"[SEED] Promoted {settings.SUPERADMIN_EMAIL} to SuperAdmin")
    finally:
        db.close()


def _get_agent_config(db: Session) -> dict:
    """Load agent config from DB."""
    configs = db.query(Config).all()
    return {c.key: c.value for c in configs}


# ─── Chat API ─────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    visitor_id: str = ""
    fingerprint: str = ""
    metadata: dict = {}


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request, db: Session = Depends(get_db)):
    # Identify / create visitor
    visitor = _get_or_create_visitor(db, req.visitor_id, req.fingerprint, req.metadata, request)

    # Start or continue conversation
    # Find open conversation (no ended_at)
    open_conv = db.query(Conversation).filter(
        Conversation.visitor_id == visitor.id,
        Conversation.channel == ChannelEnum.text,
        Conversation.ended_at == None
    ).first()

    if not open_conv:
        open_conv = Conversation(
            id=uuid.uuid4(),
            visitor_id=visitor.id,
            channel=ChannelEnum.text,
            agent=AgentEnum.sales,
        )
        db.add(open_conv)
        db.flush()

    # Save user message
    db.add(Message(
        id=uuid.uuid4(),
        conversation_id=open_conv.id,
        role=MessageRoleEnum.user,
        content=req.message,
    ))
    db.commit()

    # Get agent config from DB
    agent_config = _get_agent_config(db)
    system_prompt = agent_config.get("sales_system_prompt") or SALES_PROMPT_DEFAULT

    # Stream response
    conversation_id = str(open_conv.id)
    visitor_id = str(visitor.id)

    async def generate():
        full_response = []
        try:
            async for token in run_sales_agent_stream(
                req.message, req.history, system_prompt, agent_config
            ):
                full_response.append(token)
                yield f"data: {token}\n\n"
        finally:
            # Save assistant message
            if full_response:
                complete = "".join(full_response)
                save_db = next(get_db())
                try:
                    conv = save_db.query(Conversation).filter(Conversation.id == uuid.UUID(conversation_id)).first()
                    if conv:
                        save_db.add(Message(
                            id=uuid.uuid4(),
                            conversation_id=conv.id,
                            role=MessageRoleEnum.assistant,
                            content=complete,
                        ))
                        # Update visitor last seen
                        v = save_db.query(Visitor).filter(Visitor.id == uuid.UUID(visitor_id)).first()
                        if v:
                            v.last_seen_at = datetime.utcnow()
                        save_db.commit()
                finally:
                    save_db.close()
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _get_or_create_visitor(db: Session, anonymous_id: str, fingerprint: str, metadata: dict, request: Request) -> Visitor:
    visitor = None
    if anonymous_id:
        visitor = db.query(Visitor).filter(Visitor.anonymous_id == anonymous_id).first()

    if not visitor and fingerprint:
        visitor = db.query(Visitor).filter(Visitor.fingerprint == fingerprint).first()

    if not visitor:
        meta = {
            "user_agent": request.headers.get("user-agent"),
            "referrer": request.headers.get("referer"),
            "ip": request.client.host if request.client else None,
            **metadata,
        }
        visitor = Visitor(
            id=uuid.uuid4(),
            anonymous_id=anonymous_id or str(uuid.uuid4()),
            fingerprint=fingerprint or None,
            metadata_=meta,
        )
        db.add(visitor)
        db.flush()
    else:
        visitor.last_seen_at = datetime.utcnow()
        if fingerprint and not visitor.fingerprint:
            visitor.fingerprint = fingerprint

    db.commit()
    return visitor


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}
