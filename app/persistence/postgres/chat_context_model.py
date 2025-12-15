from sqlalchemy import Column, Integer, String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatContextModel(Base):
    __tablename__ = "chat_context"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    context_metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_chat_context_user_created", "user_id", "created_at"),
        Index("idx_chat_context_session_created", "session_id", "created_at"),
    )
