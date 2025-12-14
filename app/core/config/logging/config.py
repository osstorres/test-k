import logging
import json
from datetime import datetime
from typing import Any, Dict
import sys
from contextvars import ContextVar
from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


class CustomJSONFormatter(logging.Formatter):
    """Custom JSON formatter that ensures consistent log format."""

    def __init__(self, **kwargs):
        super().__init__()
        self.extras = kwargs

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_ctx_var.get(),
        }

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add any extras defined in formatter
        log_data.update(self.extras)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class CustomLogger:
    """Singleton logger class for consistent logging across the application."""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        """Set up the logger with custom configuration."""
        # Configure the root logger to use our custom formatter
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler with custom JSON formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            CustomJSONFormatter(app_name="LEGAL-RAG", environment="PROD")
        )

        # Add handler to root logger
        root_logger.addHandler(console_handler)

        # Also configure the specific "app" logger
        app_logger = logging.getLogger("app")
        app_logger.setLevel(logging.INFO)

        # Remove any existing handlers to avoid duplicates
        for handler in app_logger.handlers[:]:
            app_logger.removeHandler(handler)

        # Add handler to app logger
        app_logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        app_logger.propagate = False

        cls._logger = app_logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the configured logger instance."""
        if cls._logger is None:
            cls._setup_logger()
        return cls._logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid4())
        context_token = request_id_ctx_var.set(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx_var.reset(context_token)
