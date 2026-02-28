from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from database import AuditLog
import uuid


def log_action(db: Session, action: str, user_id=None, details: Optional[str] = None, ip: Optional[str] = None):
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
