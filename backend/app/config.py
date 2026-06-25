from __future__ import annotations

import os
from pathlib import Path

import yaml
from typing import Any

from pydantic import BaseModel, ConfigDict


def _load_dotenv() -> None:
    """Load environment variables from a .env file if it exists.

    Variables already set in the environment take precedence.
    Supports simple KEY=VALUE format, comments (#), and blank lines.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    loaded = 0
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Strip surrounding quotes (single or double)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            if key not in os.environ:
                os.environ[key] = value
                loaded += 1


# Load .env before any config reading
_load_dotenv()


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    api_base: str = "https://api.openai.com/v1"
    api_key: str = "sk-xxxx"
    model: str = "gpt-4o-mini"
    max_tokens: int = 2048
    temperature: float = 0.7


class AuthConfig(BaseModel):
    jwt_secret: str = "change-in-production"
    token_expire_hours: int = 24


class ObjectStorageConfig(BaseModel):
    endpoint: str = ""
    region: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "dataagent"


class DatasourceConfig(BaseModel):
    name: str
    type: str
    path: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    password: str | None = None


class EmbeddingConfig(BaseModel):
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "text-embedding-3-small"
    lancedb_path: str = "./data/lancedb"


class ToolConfig(BaseModel):
    """Definition of a tool available to the agent."""
    model_config = ConfigDict(extra="ignore")
    name: str
    description: str
    parameters: dict[str, Any] = {}
    enabled: bool = True


class WorkflowConfig(BaseModel):
    """Workflow/agent configuration."""
    model_config = ConfigDict(extra="ignore")
    mode: str = "none"  # "none" | "dynamic" | "yaml"
    tools: list[ToolConfig] = []
    yaml_dir: str = "workflows"
    max_iterations: int = 10


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = LLMConfig()
    auth: AuthConfig = AuthConfig()
    object_storage: ObjectStorageConfig = ObjectStorageConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    datasources: list[DatasourceConfig] = []
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    workflow: WorkflowConfig = WorkflowConfig()


_config: AppConfig | None = None


def _override_from_env(config: AppConfig) -> None:
    """Override config values from environment variables"""
    
    def _get_value(current: str, env_var: str) -> str:
        """Get value from env var, or use current if env var not set.
        If current is a placeholder like ${VAR}, only use env var value."""
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value
        # If current is a placeholder like ${VAR} and no env var, keep it as is
        return current
    
    # LLM config
    config.llm.api_base = _get_value(config.llm.api_base, "LLM_API_BASE")
    config.llm.api_key = _get_value(config.llm.api_key, "LLM_API_KEY")
    config.llm.model = _get_value(config.llm.model, "LLM_MODEL")
    
    # Auth config
    config.auth.jwt_secret = _get_value(config.auth.jwt_secret, "JWT_SECRET")
    if os.environ.get("TOKEN_EXPIRE_HOURS"):
        config.auth.token_expire_hours = int(os.environ["TOKEN_EXPIRE_HOURS"])
    
    # Object storage config
    config.object_storage.endpoint = _get_value(config.object_storage.endpoint, "OS_ENDPOINT")
    config.object_storage.region = _get_value(config.object_storage.region, "OS_REGION")
    config.object_storage.access_key = _get_value(config.object_storage.access_key, "OS_ACCESS_KEY")
    config.object_storage.secret_key = _get_value(config.object_storage.secret_key, "OS_SECRET_KEY")
    config.object_storage.bucket = _get_value(config.object_storage.bucket, "OS_BUCKET")
    
    # Embedding config
    config.embedding.api_base = _get_value(config.embedding.api_base, "EMBEDDING_API_BASE")
    config.embedding.api_key = _get_value(config.embedding.api_key, "EMBEDDING_API_KEY")
    config.embedding.model = _get_value(config.embedding.model, "EMBEDDING_MODEL")

    # CORS config
    if os.environ.get("CORS_ORIGINS"):
        config.cors_origins = [origin.strip() for origin in os.environ["CORS_ORIGINS"].split(",")]
    
    # Workflow config
    if os.environ.get("WORKFLOW_MODE"):
        config.workflow.mode = os.environ["WORKFLOW_MODE"]
    if os.environ.get("WORKFLOW_MAX_ITERATIONS"):
        config.workflow.max_iterations = int(os.environ["WORKFLOW_MAX_ITERATIONS"])


def load_config() -> AppConfig:
    global _config
    if _config is not None:
        return _config

    conf_path = os.environ.get("CONF_PATH", str(Path(__file__).resolve().parent.parent / "conf.yml"))
    with open(conf_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    _config = AppConfig(**raw)
    
    # Override with environment variables
    _override_from_env(_config)
    
    return _config


def get_config() -> AppConfig:
    if _config is None:
        return load_config()
    return _config
