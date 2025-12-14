from __future__ import annotations

from typing import Any, Optional
from app.core.config.logging import logger
from app.core.config.settings.kavak_config import KavakSettings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.llms import ChatMessage, LLM


class KavakLLMManager:
    _instance: Optional[KavakLLMManager] = None
    _initialized: bool = False

    def __new__(cls) -> KavakLLMManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = KavakSettings()
        self._llm: Optional[LLM] = None
        self._embedding_model: Optional[OpenAIEmbedding] = None
        self._initialized = True

        logger.info(
            f"Kavak LLM Manager initialized: provider={self.settings.llm.PROVIDER}, "
            f"model={self.settings.llm.MODEL}"
        )

    def get_llm(self, temperature: float = 0.3, max_tokens: int = 2000) -> LLM:
        return self._create_llm(temperature=temperature, max_tokens=max_tokens)

    def _create_llm(self, temperature: float = 0.3, max_tokens: int = 2000) -> LLM:
        model = self.settings.llm.MODEL

        return OpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.settings.llm.OPENAI_API_KEY,
        )

    async def complete_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000
    ) -> str:
        try:
            llm = self.get_llm(temperature=temperature, max_tokens=max_tokens)
            message = ChatMessage.from_str(prompt, role="user")
            response = await llm.achat([message])
            return str(response)
        except Exception as exc:
            logger.error(f"Error completing text: {exc}")
            raise

    async def complete_structured_text(
        self,
        prompt: str,
        response_schema: Any,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Any:
        try:
            llm = self.get_llm(temperature=temperature, max_tokens=max_tokens)

            structured_llm = llm.as_structured_llm(output_cls=response_schema)

            message = ChatMessage.from_str(prompt, role="user")
            response = await structured_llm.achat([message])

            if hasattr(response, "raw"):
                return response.raw
            elif hasattr(response, "message"):
                content = response.message.content
                if isinstance(content, str):
                    import json

                    try:
                        data = json.loads(content)
                        return response_schema(**data)
                    except (json.JSONDecodeError, ValueError):
                        return response_schema.model_validate_json(content)
                return content
            else:
                return response_schema.model_validate(response)

        except Exception as exc:
            logger.error(f"Error completing structured text: {exc}", exc_info=True)
            raise

    def _get_embedding_model(self) -> OpenAIEmbedding:
        if self._embedding_model is None:
            self._embedding_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=self.settings.llm.OPENAI_API_KEY,
            )
        return self._embedding_model

    async def embed_text(self, text: str) -> list[float]:
        try:
            embedding_model = self._get_embedding_model()
            embedding = await embedding_model.aget_text_embedding(text)
            return embedding
        except Exception as exc:
            logger.error(f"Error generating embedding: {exc}")
            raise

    def get_llama_index_llm(
        self, temperature: float = 0.7, max_tokens: int = 2000
    ) -> LLM:
        return self.get_llm(temperature=temperature, max_tokens=max_tokens)

    @classmethod
    def get_instance(cls) -> KavakLLMManager:
        if cls._instance is None:
            cls._instance = KavakLLMManager()
        return cls._instance
