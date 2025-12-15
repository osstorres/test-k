from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
from app.core.config.logging import logger
from app.core.config.database.postgres_config import PostgresSettings
from app.models.chat_interaction import (
    ChatInteraction,
    ChatInteractionCreate,
    ChatContext,
)
from app.models.persistence.chat_context_model import ChatContextModel, Base


_shared_engine = None
_shared_session_factory = None
_shared_initialized = False


class ChatContextRepository:
    def __init__(self, settings: Optional[PostgresSettings] = None):
        self.settings = settings or PostgresSettings()

    async def initialize(self):
        global _shared_engine, _shared_session_factory, _shared_initialized

        if not _shared_initialized:
            _shared_engine = create_async_engine(
                self.settings.async_database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
            _shared_session_factory = async_sessionmaker(
                _shared_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            async with _shared_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            _shared_initialized = True

    @property
    def session_factory(self):
        global _shared_session_factory
        if _shared_session_factory is None:
            raise RuntimeError("Repository not initialized. Call initialize() first.")
        return _shared_session_factory

    async def close(self):
        global _shared_engine, _shared_session_factory, _shared_initialized
        if _shared_engine:
            await _shared_engine.dispose()
            _shared_engine = None
            _shared_session_factory = None
            _shared_initialized = False

    async def add_interaction(
        self, interaction: ChatInteractionCreate
    ) -> ChatInteraction:
        await self.initialize()

        async with self.session_factory() as session:
            try:
                db_interaction = ChatContextModel(
                    user_id=interaction.user_id,
                    session_id=interaction.session_id,
                    query=interaction.query,
                    response=interaction.response,
                    intent=interaction.intent,
                    context_metadata=interaction.metadata,
                )
                session.add(db_interaction)
                await session.flush()

                await self._keep_last_n_interactions(session, interaction.user_id, n=5)

                await session.commit()
                await session.refresh(db_interaction)

                return ChatInteraction(
                    id=db_interaction.id,
                    user_id=db_interaction.user_id,
                    session_id=db_interaction.session_id,
                    query=db_interaction.query,
                    response=db_interaction.response,
                    intent=db_interaction.intent,
                    metadata=db_interaction.context_metadata,
                    created_at=db_interaction.created_at,
                )
            except Exception:
                await session.rollback()
                raise

    async def _keep_last_n_interactions(
        self, session: AsyncSession, user_id: str, n: int = 5
    ):
        try:
            subquery = (
                select(ChatContextModel.id)
                .where(ChatContextModel.user_id == user_id)
                .order_by(ChatContextModel.created_at.desc())
                .limit(n)
                .subquery()
            )

            stmt = delete(ChatContextModel).where(
                ChatContextModel.user_id == user_id,
                ~ChatContextModel.id.in_(select(subquery.c.id)),
            )
            await session.execute(stmt)
        except Exception as exc:
            logger.warning(
                f"Failed to clean old interactions for user {user_id}: {exc}"
            )

    async def get_last_interactions(
        self, user_id: str, limit: int = 5
    ) -> List[ChatInteraction]:
        await self.initialize()

        async with self.session_factory() as session:
            try:
                stmt = (
                    select(ChatContextModel)
                    .where(ChatContextModel.user_id == user_id)
                    .order_by(ChatContextModel.created_at.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                db_interactions = result.scalars().all()

                interactions = [
                    ChatInteraction(
                        id=interaction.id,
                        user_id=interaction.user_id,
                        session_id=interaction.session_id,
                        query=interaction.query,
                        response=interaction.response,
                        intent=interaction.intent,
                        metadata=interaction.context_metadata,
                        created_at=interaction.created_at,
                    )
                    for interaction in db_interactions
                ]

                return list(reversed(interactions))
            except Exception as exc:
                logger.error(
                    f"Failed to get last interactions for user {user_id}: {exc}",
                    exc_info=True,
                )
                return []

    async def get_chat_context(self, user_id: str) -> ChatContext:
        interactions = await self.get_last_interactions(user_id, limit=5)
        return ChatContext(user_id=user_id, interactions=interactions)

    async def delete_user_interactions(self, user_id: str) -> int:
        await self.initialize()

        async with self.session_factory() as session:
            try:
                stmt = delete(ChatContextModel).where(
                    ChatContextModel.user_id == user_id
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
            except Exception as exc:
                await session.rollback()
                logger.error(
                    f"Failed to delete interactions for user {user_id}: {exc}",
                    exc_info=True,
                )
                return 0
