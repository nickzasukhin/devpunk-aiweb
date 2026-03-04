import uuid
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import (
    get_db, User, AuditLog, Config, Document, Visitor, Conversation, Message,
    RoleEnum
)
from auth.middleware import get_current_user, require_superadmin
from auth.utils import hash_password
from admin.audit import log_action
from ingestion.chunker import parse_file, chunk_text
from ingestion.embedder import embed_and_store, delete_document_chunks

router = APIRouter(prefix="/admin", tags=["admin"])

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Documents ────────────────────────────────────────────────────────────────

@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed = {".md", ".txt", ".pdf", ".json"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    text = parse_file(content, file.filename)
    chunks = chunk_text(text)

    db_config = {c.key: c.value for c in db.query(Config).all()}
    api_key = db_config.get("openai_api_key") or None

    doc_id = str(uuid.uuid4())
    count = embed_and_store(chunks, doc_id, file.filename, api_key=api_key)

    doc = Document(
        id=uuid.UUID(doc_id),
        filename=file.filename,
        file_type=ext.lstrip("."),
        chunk_count=count,
        status="indexed",
        uploaded_by=current_user.id
    )
    db.add(doc)
    db.commit()

    log_action(db, current_user.id, "upload_document", f"file={file.filename} chunks={count}",
               request.client.host if request.client else None)
    return {"id": doc_id, "filename": file.filename, "chunk_count": count}


@router.get("/documents")
async def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [{"id": str(d.id), "filename": d.filename, "file_type": d.file_type,
             "chunk_count": d.chunk_count, "status": d.status,
             "uploaded_at": d.uploaded_at.isoformat()} for d in docs]


@router.post("/documents/{doc_id}/reindex")
async def reindex_document(doc_id: str, request: Request, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    saved_path = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(saved_path):
        raise HTTPException(404, "File not found on disk")

    with open(saved_path, "rb") as f:
        content = f.read()

    db_config = {c.key: c.value for c in db.query(Config).all()}
    api_key = db_config.get("openai_api_key") or None

    delete_document_chunks(doc_id)
    text = parse_file(content, doc.filename)
    chunks = chunk_text(text)
    count = embed_and_store(chunks, doc_id, doc.filename, api_key=api_key)

    doc.chunk_count = count
    doc.status = "indexed"
    db.commit()
    log_action(db, current_user.id, "reindex_document", f"file={doc.filename}", request.client.host if request.client else None)
    return {"chunk_count": count}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, request: Request, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    delete_document_chunks(doc_id)
    db.delete(doc)
    db.commit()
    log_action(db, current_user.id, "delete_document", f"file={doc.filename}", request.client.host if request.client else None)
    return {"status": "deleted"}


# ─── Config ───────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    MASKED = {"anthropic_api_key", "openai_api_key", "elevenlabs_api_key", "vapi_api_key"}
    configs = db.query(Config).all()
    result = {}
    for c in configs:
        result[c.key] = "***" if c.key in MASKED and c.value else c.value
    return result


@router.put("/config")
async def update_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    body = await request.json()
    for key, value in body.items():
        if value == "***":
            continue  # don't overwrite masked values
        cfg = db.query(Config).filter(Config.key == key).first()
        if cfg:
            cfg.value = str(value)
            cfg.updated_at = datetime.utcnow()
            cfg.updated_by = current_user.id
        else:
            db.add(Config(key=key, value=str(value), updated_by=current_user.id))

    db.commit()
    log_action(db, current_user.id, "update_config", f"keys={list(body.keys())}", request.client.host if request.client else None)
    return {"status": "updated"}


# ─── Users (SuperAdmin only) ──────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: str
    password: str


@router.get("/users")
async def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    users = db.query(User).all()
    return [{"id": str(u.id), "email": u.email, "role": u.role, "is_active": u.is_active,
             "created_at": u.created_at.isoformat(), "last_login": u.last_login.isoformat() if u.last_login else None}
            for u in users]


@router.post("/users")
async def create_user(req: CreateUserRequest, request: Request, db: Session = Depends(get_db),
                      current_user: User = Depends(require_superadmin)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already exists")
    user = User(id=uuid.uuid4(), email=req.email, hashed_password=hash_password(req.password), role=RoleEnum.admin)
    db.add(user)
    db.commit()
    log_action(db, current_user.id, "create_user", f"email={req.email}", request.client.host if request.client else None)
    return {"id": str(user.id), "email": user.email}


@router.patch("/users/{user_id}/toggle")
async def toggle_user(user_id: str, request: Request, db: Session = Depends(get_db),
                      current_user: User = Depends(require_superadmin)):
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == RoleEnum.superadmin:
        raise HTTPException(400, "Cannot deactivate SuperAdmin")
    user.is_active = not user.is_active
    db.commit()
    log_action(db, current_user.id, "toggle_user", f"email={user.email} active={user.is_active}", request.client.host if request.client else None)
    return {"is_active": user.is_active}


@router.patch("/users/{user_id}/password")
async def reset_user_password(user_id: str, request: Request, db: Session = Depends(get_db),
                               current_user: User = Depends(require_superadmin)):
    body = await request.json()
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.hashed_password = hash_password(body["password"])
    db.commit()
    log_action(db, current_user.id, "reset_user_password", f"email={user.email}", request.client.host if request.client else None)
    return {"status": "updated"}


# ─── Audit Log (SuperAdmin only) ──────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin),
                        limit: int = 100, offset: int = 0):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [{"id": str(l.id), "user_id": str(l.user_id) if l.user_id else None,
             "action": l.action, "details": l.details, "ip": l.ip_address,
             "created_at": l.created_at.isoformat()} for l in logs]


# ─── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations/visitors")
async def list_visitors(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    visitors = db.query(Visitor).order_by(Visitor.last_seen_at.desc()).all()
    result = []
    for v in visitors:
        conv_count = db.query(Conversation).filter(Conversation.visitor_id == v.id).count()
        result.append({
            "id": str(v.id),
            "anonymous_id": v.anonymous_id,
            "first_seen_at": v.first_seen_at.isoformat(),
            "last_seen_at": v.last_seen_at.isoformat(),
            "metadata": v.metadata_,
            "conversation_count": conv_count,
        })
    return result


@router.get("/conversations/visitors/{visitor_id}")
async def get_visitor_conversations(visitor_id: str, db: Session = Depends(get_db),
                                    current_user: User = Depends(get_current_user)):
    visitor = db.query(Visitor).filter(Visitor.id == uuid.UUID(visitor_id)).first()
    if not visitor:
        raise HTTPException(404, "Visitor not found")

    conversations = db.query(Conversation).filter(Conversation.visitor_id == visitor.id).order_by(Conversation.started_at.desc()).all()
    result = []
    for c in conversations:
        msgs = [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in c.messages]
        result.append({
            "id": str(c.id),
            "channel": c.channel,
            "agent": c.agent,
            "started_at": c.started_at.isoformat(),
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "audio_url": c.audio_url,
            "messages": msgs,
        })
    return {"visitor": {"id": str(visitor.id), "anonymous_id": visitor.anonymous_id, "metadata": visitor.metadata_}, "conversations": result}
