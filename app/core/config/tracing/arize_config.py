from typing import Optional
from app.core.config.logging import logger
from app.core.config.settings.kavak_config import ArizeSettings


def setup_arize_tracing(
    arize_settings: Optional[ArizeSettings] = None,
) -> Optional[object]:
    try:
        from arize.otel import register
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

        space_id = arize_settings.SPACE_ID
        api_key = arize_settings.API_KEY
        project_name = arize_settings.PROJECT_NAME

        if not space_id or not api_key:
            logger.warning("Arize AX credentials not configured. ")
            return None

        tracer_provider = register(
            space_id=space_id,
            api_key=api_key,
            project_name=project_name,
        )

        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(
            f"Arize AX tracing initialized successfully for project: {project_name}"
        )

        return tracer_provider

    except Exception as e:
        logger.error(f"Failed to initialize Arize AX tracing: {e}", exc_info=True)
        return None
