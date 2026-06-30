# DataAgent

**DataAgent** is an open-source, web-based intelligent assistant for data exploration. It enables users to interact with their business data through natural language conversations powered by LLMs. With built-in tools for SQL execution, schema exploration, and file browsing, DataAgent bridges the gap between domain users and their databases.

![query sample](./docs/screen_sample.gif)

## Features

- **Natural language data exploration** -- Ask questions about your data and get answers with real-time SQL execution
- **Three workflow modes** -- Choose between simple chat, autonomous ReAct agent loops with tool-calling, or predefined YAML workflows
- **Real-time streaming** -- Responses appear character-by-character via Server-Sent Events (SSE)
- **Rich markdown rendering** -- Code blocks, tables, and structured responses rendered with GitHub Flavored Markdown
- **Context injection** -- Select files from object storage or reference database tables; schemas are automatically injected into the LLM prompt
- **Full debugging transparency** -- Inspect every LLM request/response, including prompts, parameters, token usage, and timing
- **Business ontology system** -- Model your business domain (activities, objects, rules, metrics) and let the LLM understand how concepts map to database tables
- **Multi-tenant support** -- Isolated datasources, ontologies, and users per tenant
- **Skill system** -- Keyword-triggered YAML skills provide domain-specific guidance to the LLM
- **Vector embeddings** -- LanceDB integration for semantic search over business knowledge
- **Multi-language UI** -- Frontend internationalization via i18next
- **Conversation memory** -- Long conversations are automatically summarized to stay within context limits

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Sidebar  │  │    Chat Area     │  │  Resource Panel   │  │
│  │(history) │  │  (SSE streaming) │  │(Storage/Data/WF)  │  │
│  └──────────┘  └──────────────────┘  └───────────────────┘  │
│                       │                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Debug Drawer (LLM trace)                  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP/SSE
┌─────────────────────────▼─────────────────────────────────┐
│  FastAPI Backend (port 8010)                               │
│  ┌────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │   Router   │→ │   Service   │→ │       DB          │   │
│  │  (HTTP)    │  │ (business)  │  │  (SQLAlchemy)     │   │
│  └────────────┘  └─────────────┘  └───────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┼──────────────────────────────┐   │
│  │  Workflow Dispatcher                                  │   │
│  │  ┌─────────┐  ┌────────────┐  ┌─────────────────┐   │   │
│  │  │  none   │  │  dynamic   │  │     yaml        │   │   │
│  │  │(stream) │  │(agent loop)│  │(step templates) │   │   │
│  │  └─────────┘  └────────────┘  └─────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┼──────────────────────────────┐   │
│  │              Tool Registry                           │   │
│  │  execute_sql │ list_tables │ get_table_schema      │   │
│  │  read_file   │ list_files                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌───────────┐  ┌────────────┐  ┌───────────────┐
   │ PostgreSQL│  │  OpenAI-   │  │   Object      │
   │  / SQLite │  │  compatible│  │   Storage     │
   │           │  │  LLM API   │  │   (TOS/S3)    │
   └───────────┘  └────────────┘  └───────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS, Zustand |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL (production) / SQLite (development) |
| LLM | Any OpenAI-compatible API (DeepSeek, GPT-4o, MiniMax, etc.) |
| Vector DB | LanceDB |
| Object Storage | Volcengine TOS (S3-compatible) |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An API key from an OpenAI-compatible LLM provider

### Docker Compose (Recommended)

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your LLM_API_KEY and other settings

# 2. Start services
bash scripts/build.sh

# 3. Access the application
# Frontend: http://localhost:9280
# Backend API: http://localhost:8010
```

This starts PostgreSQL 16, the FastAPI backend, and the React frontend behind Nginx.

For a clean rebuild (stop and remove all containers, remove old images, rebuild and restart):

```bash
bash scripts/build.sh
```

### Local Development

**Backend:**

```bash
cd backend
uv sync
cp .env.example .env   # Configure your LLM_API_KEY
uv run uvicorn app.main:app --reload --port 8010
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev   # Proxies /api to localhost:8010
```

> The dev server runs at `http://localhost:3000` and proxies API requests to the backend via Vite.

### Testing

```bash
cd backend
uv run pytest tests/ -v
```

## Configuration

All settings are in `backend/conf.yml` with environment variable overrides available. Key settings:

| Setting | Env Variable | Description |
|---------|-------------|-------------|
| `llm.api_base` | `LLM_API_BASE` | OpenAI-compatible API endpoint |
| `llm.api_key` | `LLM_API_KEY` | API key for the LLM provider |
| `llm.model` | `LLM_MODEL` | Model name (e.g., `gpt-4o-mini`) |
| `auth.jwt_secret` | `JWT_SECRET` | Secret for signing JWT tokens |
| `workflow.mode` | `WORKFLOW_MODE` | `none`, `dynamic`, or `yaml` |
| `workflow.max_iterations` | `WORKFLOW_MAX_ITERATIONS` | Max tool-calling loop iterations |

### Workflow Modes

| Mode | Description |
|------|------------|
| `none` | Simple chat with streaming responses, no tool calls |
| `dynamic` | **ReAct agent loop** -- the LLM autonomously decides which tools to call, up to `max_iterations` |
| `yaml` | Predefined workflows with keyword matching and template-based step resolution |

You can also override the mode per request via the `workflow_mode` field in the chat API.

### Built-in Tools

| Tool | Description |
|------|------------|
| `execute_sql` | Execute read-only SELECT queries on configured datasources |
| `list_tables` | List all tables across configured datasources |
| `get_table_schema` | Get column names and types for a specific table |
| `read_file` | Read file content from object storage |
| `list_files` | List files and directories in object storage |

## Project Structure

```
MaoDataAgent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point, lifespan events
│   │   ├── config.py            # Configuration (YAML + env vars)
│   │   ├── auth.py              # JWT + bcrypt authentication
│   │   ├── models/schemas.py    # Pydantic request/response models
│   │   ├── db/                  # SQLAlchemy ORM models + CRUD operations
│   │   ├── router/              # HTTP route handlers (thin layer)
│   │   ├── service/             # Business logic
│   │   │   ├── chat.py          # Chat streaming + mode dispatcher
│   │   │   ├── agent.py         # Dynamic ReAct agent loop
│   │   │   ├── engine.py        # YAML workflow engine
│   │   │   ├── tools.py         # Tool registry + implementations
│   │   │   └── ...
│   │   ├── ontology/            # Business ontology management
│   │   └── embedding/           # LanceDB vector embeddings
│   ├── skills/                  # YAML skill definitions
│   ├── workflows/               # YAML workflow definitions
│   ├── conf.yml                 # Configuration file
│   ├── pyproject.toml
│   └── tests/                   # pytest test suite
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Root component (auth gating)
│   │   ├── store.ts              # Zustand state management
│   │   ├── api.ts                # API client + SSE streaming
│   │   └── components/           # React components
│   │       ├── Layout.tsx        # Three-column layout
│   │       ├── ChatArea.tsx      # Chat + SSE streaming
│   │       ├── SidebarHistory.tsx
│   │       ├── ResourcePanel.tsx
│   │       ├── DebugDrawer.tsx
│   │       ├── WorkflowPanel.tsx
│   │       └── ...
│   ├── package.json
│   └── vite.config.ts
├── docs/                         # Documentation
│   ├── DESIGN.md                 # Technical design document
│   ├── Business_schema.md        # Procurement domain schema
│   └── Ontology_schema.md        # Ontology system schema
├── docker-compose.yml
└── LICENSE
```

## API Overview

All endpoints return JSON except `POST /api/chat/stream` which returns SSE.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login, returns JWT + user info |
| GET | `/api/auth/me` | Current user profile |
| GET/POST/DELETE | `/api/conversations[/{id}]` | Conversation CRUD |
| POST | `/api/chat/stream` | Streaming chat (SSE) |
| GET | `/api/storage/list` | List files from object storage |
| GET | `/api/storage/read` | Read file from object storage |
| GET | `/api/datasource/tables` | List tables from datasources |
| GET | `/api/datasource/table/{table}/columns` | Get table column definitions |
| GET | `/api/debug/{message_id}` | Get LLM request/response debug info |
| GET | `/api/workflow/executions/{id}` | Get workflow execution details |

See [docs/DESIGN.md](docs/DESIGN.md) for full API specifications.

## Security

- JWT-based authentication on all endpoints except login
- Password hashing via bcrypt
- Resource ownership validation on all user-specific endpoints
- SQL injection prevention through table name regex validation and parameterized queries
- `execute_sql` tool restricted to SELECT statements (read-only)

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Documentation

- [Technical Design](docs/DESIGN.md) -- Full architecture, API specs, component tree
- [Business Schema](docs/Business_schema.md) -- Procurement/warehousing domain model
- [Ontology Schema](docs/Ontology_schema.md) -- Business ontology and metadata tables
