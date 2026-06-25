from __future__ import annotations

import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import load_config
from app.db.database import close_db, init_tables
from app.router import auth, chat, conversation, datasource, debug, storage, workflow, tools_test, user_datasource, skills, tenant
from app.ontology.router import router as ontology_router
from app.embedding.router import router as embedding_router
import app.db.business_models  # noqa: F401 — register business domain models with Base.metadata

logger = logging.getLogger("dataagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Stream handler (console) — uvicorn may have added its own, but this ensures
    # a consistent formatter for all log output.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_fmt))
    root.addHandler(console_handler)

    log_dir = os.environ.get("LOG_DIR", str(Path(__file__).resolve().parent / "logs"))
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "data_agent.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_fmt))
    root.addHandler(file_handler)

    logger.info("Starting up...")

    logger.info("Loading configuration...")
    config = load_config()
    logger.info("Config loaded: LLM model=%s, api_base=%s", config.llm.model, config.llm.api_base)
    logger.info("Config loaded: auth token_expire_hours=%d", config.auth.token_expire_hours)
    logger.info("Config loaded: object_storage endpoint=%s, bucket=%s", config.object_storage.endpoint, config.object_storage.bucket)
    logger.info("Config loaded: datasources=%s", [ds.name for ds in config.datasources])

    logger.info("Initializing database...")
    try:
        await init_tables()
        from app.embedding.embedding_store import init_embedding_store
        await init_embedding_store()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise e
    from app.seed.pwd_utils import init_pwd
    await init_pwd()

    # Register built-in tools for dynamic/yaml workflow modes
    from app.service.tools import register_builtin_tools
    register_builtin_tools()

    # Load skills
    from app.service.skills import skill_registry
    skill_registry.load()

    # Ensure default datasource configs for all users
    from app.db.user_datasource_db import init_default_datasources
    await init_default_datasources()

    # Auto-seed sample manufacturing data (idempotent)
    from app.seed.sample_data_seed import init_sample_data
    await init_sample_data()
    logger.info("Sample data seed complete")
    logger.info("Default datasource configs ensured")

    logger.info("DataAgent backend started successfully")
    yield  # 应用运行期
    # --- 关闭逻辑 (替代 @app.on_event("shutdown")) ---
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(title="DataAgent", lifespan=lifespan)

# Configure CORS
config = load_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(conversation.router)
app.include_router(chat.router)
app.include_router(storage.router)
app.include_router(datasource.router)
app.include_router(debug.router)
app.include_router(workflow.router)
app.include_router(ontology_router)
app.include_router(embedding_router)
app.include_router(tools_test.router)
app.include_router(user_datasource.router)
app.include_router(tenant.router)
app.include_router(skills.router)

    
