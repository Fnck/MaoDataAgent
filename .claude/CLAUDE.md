# Project: DataAgent

An LLM-powered intelligent data exploration assistant with ~13,400 lines of code across ~60 source files.

## 1. Tech Stack
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0+ (async) + aiosqlite + uv
- **Frontend:** Vite 6 + React 19 + TypeScript 5.8 (strict) + TailwindCSS 3.4 + Zustand 5
- **Database:** SQLite via SQLAlchemy ORM (Alembic migrations, 2 versions)
- **Object Storage:** Volcengine TOS (tos==2.9.0 SDK)
- **LLM:** OpenAI-compatible API (openai SDK), default model MiniMax M2.5
- **SQL Analysis:** sqlglot>=30.8.0 (for CPT parser)
- **Deployment:** Docker Compose (backend:8010, frontend:9280)

## 2. Project Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan (startup/shutdown)
│   ├── config.py             # Pydantic config models, loads conf.yml + env overrides
│   ├── auth.py               # JWT creation/verification via python-jose, bcrypt hashing
│   ├── seed.py               # Creates initial admin user on startup (default: admin/admin123)
│   ├── doc_parser.py         # Standalone CPT parsing entry point
│   ├── cpt_parser/           # CPT file analysis subsystem (FineReport/ClickHouse)
│   │   ├── __init__.py       # Module entry, analyze_cpt_file() pipeline
│   │   ├── sql_analyzer.py   # SQL analysis using sqlglot (19.9 KB)
│   │   ├── template_preprocessor.py  # CPC template handling
│   │   ├── physical_resolver.py      # Physical table/join resolution via CTE expansion
│   │   ├── xml_parser.py     # CPT XML file parser
│   │   ├── llm_enricher.py   # LLM-based description enrichment
│   │   └── models.py         # CPT analysis domain models
│   ├── pdf_pic_extract/      # PDF picture extraction (in-progress, empty)
│   ├── router/               # Thin route handlers (HTTP → service)
│   │   ├── auth.py           # POST /api/auth/login, GET /api/auth/me
│   │   ├── conversation.py   # CRUD for conversations
│   │   ├── chat.py           # POST /api/chat/stream (SSE)
│   │   ├── storage.py        # GET /api/storage/list, /api/storage/read
│   │   ├── datasource.py     # GET /api/datasource/tables, /columns
│   │   ├── debug.py          # GET /api/debug/conversation/{id}
│   │   └── workflow.py       # GET /api/workflow/executions/{id}, /conversations/{id}/executions
│   ├── service/              # Business logic
│   │   ├── chat.py           # LLM streaming, context injection, mode dispatcher (none|dynamic|yaml)
│   │   ├── agent.py          # Dynamic agent loop: LLM tool-calling with max_iterations guard
│   │   ├── engine.py         # YAML workflow engine: keyword matching, template resolution, step execution
│   │   ├── tools.py          # Tool registry + 5 built-in tools
│   │   ├── storage.py        # TOS object storage client (list_files, read_file)
│   │   ├── datasource.py     # Database metadata reader (SQLite only)
│   │   ├── debug.py          # Debug event retrieval service
│   │   └── debug_bus.py      # Per-request debug event bus (asyncio.Queue)
│   ├── db/                   # Database layer
│   │   ├── session.py        # AsyncEngine, async_session_factory, get_async_session dependency
│   │   ├── models.py         # ORM models: User, Conversation, Message, DebugEvent, WorkflowExecution, WorkflowStep
│   │   ├── database.py       # CRUD for users, conversations, messages, debug_events
│   │   └── workflow_db.py    # CRUD for workflow_executions, workflow_steps
│   └── models/               # Pydantic schemas
│       └── schemas.py        # All request/response models (LoginRequest, ChatRequest, SSE events, etc.)
├── alembic/                  # Database migrations (2 versions)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── ffb68fdb137e_initial_schema.py
│       └── a1b2c3d4e5f6_add_debug_events_drop_debug_logs.py
├── workflows/                # YAML workflow definitions
│   └── explore_table.yaml    # Sample: get schema + list tables → final answer
├── tests/                    # pytest test suite (59 tests)
│   ├── conftest.py           # Test fixtures (db_session, test_config)
│   ├── test_tools.py         # 17 tests: tool registration, execution, safety checks
│   ├── test_engine.py        # 18 tests: _load_workflows, _match_workflow, _resolve_template
│   ├── test_agent.py         # 6 tests: agent loop logic
│   └── test_workflow_db.py   # 18 tests: workflow execution CRUD
├── conf.yml                  # Configuration (LLM, auth, object_storage, datasources, workflow)
├── pyproject.toml            # Dependencies via uv
├── verify_cpt.py             # CPT parser verification script
└── Dockerfile

frontend/
├── src/
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Root component (auth guard: LoginPage or Layout)
│   ├── api.ts                # API client + SSE streaming (ReadableStream parser)
│   ├── store.ts              # Zustand store (auth, conversations, messages, context, UI, debug, workflowSteps, streaming)
│   ├── types.ts              # TypeScript interfaces (User, Message, SSEEvent, WorkflowStep, DebugEvent, etc.)
│   ├── index.css             # TailwindCSS directives + custom scrollbar styles
│   └── components/
│       ├── Layout.tsx        # Three-column layout with collapsible sidebars
│       ├── LoginPage.tsx     # Username/password login form
│       ├── SidebarHistory.tsx # Conversation list, create/delete/switch
│       ├── ResourcePanel.tsx # Right panel: Storage, Data Sources, Workflow tabs
│       ├── ChatArea.tsx      # Message bubbles, SSE streaming, react-markdown rendering, debug button
│       ├── DebugDrawer.tsx   # Slide-out overlay with filterable debug events, copy JSON
│       ├── DebugCard.tsx     # Individual debug event card (expandable JSON detail)
│       └── WorkflowPanel.tsx # Step timeline visualization (running/completed/failed)
├── nginx.conf                # Production: proxy /api to backend:8010 + SPA fallback, SSE support
├── package.json
├── vite.config.ts            # Dev proxy /api → localhost:8000
├── tailwind.config.js        # TailwindCSS + @tailwindcss/typography plugin
├── tsconfig.json             # TypeScript strict mode
└── Dockerfile                # Multi-stage: node build → nginx serve
```

## 3. Database Schema (SQLite via SQLAlchemy, 6 tables)

```
users ──< conversations ──< messages ──< debug_events
                                  │
                                  ├──< workflow_executions ──< workflow_steps
                                  └──< debug_events
```

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `users` | id, username, password_hash | User authentication |
| `conversations` | id, user_id (FK), title, created_at | Chat sessions |
| `messages` | id, conversation_id (FK, CASCADE), role, content, created_at | Chat messages |
| `debug_events` | id, conversation_id (FK), message_id (FK, nullable), step_id (FK, nullable), category, data (JSON text), timestamp | Debug logging (categories: llm_call, tool_call, context, system) |
| `workflow_executions` | id, conversation_id (FK, CASCADE), message_id (FK, nullable), mode, workflow_name, status, final_answer, started_at, finished_at | Workflow runs |
| `workflow_steps` | id, execution_id (FK, CASCADE), step_index, step_type, step_name, input, output, status, error, started_at, finished_at | Individual steps |

**Note:** `debug_logs` table was dropped in migration `a1b2c3d4e5f6` and replaced by `debug_events`.

## 4. Workflow Modes
Configured via `workflow.mode` in conf.yml (or `WORKFLOW_MODE` env var):

| Mode | Behavior |
|------|----------|
| `none` (default) | Simple chat: LLM responds directly with streaming |
| `dynamic` | Agent loop: LLM decides tools to call (max_iterations), ReAct pattern |
| `yaml` | Predefined workflows: keyword-matched YAML definitions with fixed steps |

Per-request override available via `workflow_mode` field in ChatRequest.

### SSE Event Types
| Type | Fields | When |
|------|--------|------|
| `chunk` | content | Streaming text from LLM |
| `end` | message_id | Stream complete |
| `error` | error | Error occurred |
| `step_start` | step_id, step_name, step_type | Workflow step begins |
| `step_chunk` | step_id, content | Streaming within a step |
| `step_end` | step_id, output | Step completes successfully |
| `step_error` | step_id, error | Step fails |

### Tool Registry
Five built-in tools registered at startup in `tools.py`:
- `execute_sql` — Execute SELECT queries against configured datasources (read-only enforced)
- `list_tables` — List all tables from all datasources
- `get_table_schema` — Get column definitions for a table (format: `datasource_name.table_name`)
- `read_file` — Read file content from object storage by key
- `list_files` — List files/directories in object storage at a prefix

### CPT Parser Subsystem (`app/cpt_parser/`)
Specialized module for analyzing FineReport CPT (ClickHouse Pipeline Template) files:
- **XML Parsing** (`xml_parser.py`) — Parses CPT XML structure
- **Template Preprocessing** (`template_preprocessor.py`) — Handles CPC template syntax
- **SQL Analysis** (`sql_analyzer.py`, 19.9 KB) — Uses `sqlglot>=30.8.0` to parse and analyze ClickHouse SQL
- **Physical Resolution** (`physical_resolver.py`) — Resolves logical tables to physical relations via CTE expansion
- **LLM Enrichment** (`llm_enricher.py`) — Uses LLM to enrich analysis with business context
- Accessed via `analyze_cpt_file()` in `__init__.py`, standalone entry via `verify_cpt.py`

## 5. External Integrations

| Integration | Purpose | SDK |
|-------------|---------|-----|
| MiniMax M2.5 | LLM backend (OpenAI-compatible API) | `openai` Python SDK |
| Volcengine TOS | Object storage (file browse, read) | `tos==2.9.0` |
| ClickHouse CPT | Data pipeline template analysis | Custom parser + `sqlglot>=30.8.0` |

## 6. Coding Rules
- **Backend layer separation:** router (thin) → service (logic) → db (data). Routers handle HTTP concerns; services raise `ValueError`/`PermissionError`; routers convert to `HTTPException`
- **Async all the way:** All DB operations use async SQLAlchemy sessions
- **Frontend:** TypeScript strict mode; no `any` type; use Zustand for state; no React Router (single-page, auth-gated)
- **API auth:** all endpoints except `POST /api/auth/login` require `Authorization: Bearer <JWT>`
- **Ownership:** all user-specific endpoints must validate resource ownership
- **Password hashing:** use `bcrypt` directly (not passlib)
- **Object storage:** use `tos` SDK (not boto3)
- **ORM:** Use SQLAlchemy ORM (`app/db/models.py`) with Alembic migrations; no raw SQL for application logic
- **SQL safety:** `execute_sql` tool must enforce SELECT-only; table names validated via `^[a-zA-Z0-9_]+$` regex
- **Debug events:** Use `DebugEventBus` (per-request asyncio.Queue) for emitting debug events during SSE streaming; events persisted to `debug_events` table

## 7. API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Login → JWT + user info |
| GET | /api/auth/me | Current user profile |
| GET | /api/conversations | List user conversations |
| POST | /api/conversations | Create conversation |
| GET | /api/conversations/{id} | Get conversation with messages |
| DELETE | /api/conversations/{id} | Delete conversation |
| POST | /api/chat/stream | SSE streaming chat |
| GET | /api/storage/list | List object storage files |
| GET | /api/storage/read | Read text file from storage |
| GET | /api/datasource/tables | List tables from datasources |
| GET | /api/datasource/table/{table}/columns | Get table columns |
| GET | /api/debug/conversation/{id} | Get debug events for conversation |
| GET | /api/workflow/executions/{id} | Get workflow execution with steps |
| GET | /api/workflow/conversations/{id}/executions | List executions for a conversation |

## 8. Configuration (conf.yml)
```yaml
llm:
  api_base: "https://aimodels.example.com/v1"
  api_key: "sk-xxxx"              # Override: LLM_API_KEY env var
  model: "openai/MiniMax-M2.5"
  max_tokens: 20480
  temperature: 0.7

auth:
  jwt_secret: "change-in-production"  # Override: JWT_SECRET env var
  token_expire_hours: 24

object_storage:
  endpoint: "tos-cn-beijing.volces.com"
  region: "cn-beijing"
  access_key: ""                  # Override: OS_ACCESS_KEY env var
  secret_key: ""                  # Override: OS_SECRET_KEY env var
  bucket: "dataagent"

datasources:
  - name: "sample_db"
    type: "sqlite"
    path: "./data/sample.db"

workflow:
  mode: "none"                    # "none" | "dynamic" | "yaml"
  max_iterations: 10
  yaml_dir: "workflows"
  tools:
    - name: "execute_sql"
      description: "..."
      parameters: { datasource_name: { type: string }, query: { type: string } }
      enabled: true
    # ... list_tables, get_table_schema, read_file, list_files
```

## 9. Running Locally
```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --port 8000

# Frontend (proxies /api to localhost:8000 via vite.config.ts)
cd frontend && npm install && npm run dev

# Seed initial user (runs automatically on startup, defaults: admin/admin123)
cd backend && uv run python -m seed --username admin --password admin123
```

## 10. Testing
```bash
cd backend && uv run pytest tests/ -v
```
59 tests across 4 test files: tools (17), engine (18), agent (6), workflow_db (18).

## 11. Design Document
See `docs/DESIGN.md` for full architecture and specification.

## 12. Adjacent Architecture (Knora Platform)
This project sits within a larger platform defined in `Knora_Arch.md`. Key adjacent services (not in this repo):
- **Container:** knora-ontology-aigo, base-server (MySQL), redis, postgresql/pgvector, minio, elasticsearch, knora-web, dsm-web, knora-claw (agent), spotlight-server (MCP), selenium, doc-analysis, sandbox, uums-web (user mgmt)
- **Non-container:** Apache Doris, scopa (graph analysis), sigmaweb/glightweb (data dev platforms), Zookeeper, Flink, DolphinScheduler, Spark