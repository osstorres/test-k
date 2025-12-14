"""
Types Configuration

Type definitions and enums for application settings.
"""

from enum import Enum


class Environment(str, Enum):
    """Application environment types."""

    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"
